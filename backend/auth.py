import os
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

import models
from database import get_db

SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day -- fine for testing

# Kept around in case passwords ever get migrated to proper hashes.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, stored: str) -> bool:
    """SalEmployee.Password started life as VARCHAR(10) -- too short for a
    bcrypt hash -- so old rows created directly in the legacy desktop app
    are plaintext. The ERP admin backend (security.py) now hashes every
    password it sets with bcrypt into a widened VARCHAR(255) column, so
    any employee created or edited through that admin panel has a real
    bcrypt hash instead.

    Both shapes exist in the same column right now, so detect which one
    we're looking at rather than assuming: bcrypt hashes always start
    with one of these three prefixes; anything else is treated as the
    legacy plaintext value.
    """
    if stored.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            return pwd_context.verify(plain, stored)
        except ValueError:
            # Malformed hash -- fall through to a plain compare rather
            # than 500ing the login.
            return plain == stored
    return plain == stored


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = (
        db.query(models.SalEmployee)
        .filter(models.SalEmployee.UserName == username)
        .first()
    )
    if user is None:
        raise credentials_exception
    return user