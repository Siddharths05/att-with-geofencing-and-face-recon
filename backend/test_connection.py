import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Trying to connect using: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print("✅ Connected successfully!")
        print("Postgres version:", result.fetchone()[0])
except Exception as e:
    print("❌ Connection failed:")
    print(e)
