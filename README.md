# Geo Attendance App

A simple attendance system that marks a user present only if they check in
from within a set radius of the office. Backend is a FastAPI service with a
PostgreSQL database; frontend is a React Native (Expo) app.

## Features

- Email/password signup and login with JWT authentication
- Check-in endpoint that calculates distance from the office using the
  Haversine formula and accepts or rejects the check-in based on a
  configurable radius
- Attendance history per user
- Monthly calendar view showing present/rejected/absent days, with a
  summary count for the month
- Light, dark, and reader (sepia) themes on the frontend, with the choice
  persisted on the device

## Tech stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL, python-jose (JWT), passlib
(bcrypt), Pydantic

**Frontend:** React Native (Expo), React Navigation, expo-location,
AsyncStorage, react-native-calendars

## Project structure

```
backend/
  main.py       # FastAPI app, routes, distance calculation
  models.py     # SQLAlchemy models (User, Attendance)
  schemas.py    # Pydantic request/response schemas
  auth.py       # Password hashing, JWT creation/validation, current-user dependency
  database.py   # Engine, session, Base

frontend/
  App.js                     # Navigation setup, wraps app in ThemeProvider
  theme.js                   # Color palettes and design tokens (light/dark/reader)
  ThemeContext.js            # Theme state, persistence, and mode switching
  screens/
    LoginScreen.js
    AttendanceScreen.js
    AttendanceCalendarScreen.js
```

## Backend setup

1. Create a PostgreSQL database.
2. Create a `.env` file in the backend directory:

   ```
   DATABASE_URL=postgresql://<user>:<password>@localhost:5432/<database_name>
   SECRET_KEY=<a long random string>
   ```

3. Install dependencies and run:

   ```
   pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib[bcrypt] python-dotenv pydantic[email]
   uvicorn main:app --reload
   ```

   Tables are created automatically on startup if they don't already exist.

4. Set the office coordinates and allowed radius in `main.py`:

   ```python
   OFFICE_LAT = 19.204443
   OFFICE_LON = 72.970067
   ALLOWED_RADIUS_METERS = 50
   ```

## API endpoints

| Method | Path                   | Auth required | Description                              |
|--------|------------------------|----------------|-------------------------------------------|
| POST   | `/signup`               | No             | Create a user, returns an access token    |
| POST   | `/login`                | No             | Log in, returns an access token           |
| POST   | `/attendance/check-in`  | Yes            | Check in with lat/lon, marked present or rejected based on distance |
| GET    | `/attendance/history`   | Yes            | List all past check-ins for the current user |
| GET    | `/attendance/calendar`  | Yes            | Day-by-day status for a given month (`?year=&month=`), plus a summary |

Auth uses a bearer token: `Authorization: Bearer <access_token>`.

## Frontend setup

1. Install dependencies:

   ```
   npm install
   npm install react-native-calendars
   ```

2. Point the app at your backend by setting the base URL in `api.js`.
3. Start the app:

   ```
   npx expo start
   ```

## Themes

The app ships with three themes: light (white + purple), dark (black +
purple), and reader (sepia + warm brown). Tap the theme icon on the login
or attendance screen to cycle through them. Light and dark can also follow
the device's system setting until the user picks one manually; the
selection is saved with AsyncStorage so it persists between app launches.

## Notes

- CORS is currently wide open (`allow_origins=["*"]`) for local development
  and should be restricted before deploying anywhere public.
- The office location check uses straight-line (great-circle) distance, not
  walking distance, so results near buildings or dense areas may be
  approximate.
- There is currently no restriction preventing multiple check-ins on the
  same day; the calendar view treats a day as "present" if any check-in
  that day succeeded.# geo-final
