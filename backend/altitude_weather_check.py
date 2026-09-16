"""
Prototype: weather-adjusted altitude check, generalized per-site so it works
for any company's office coordinates, not one hardcoded location.

Pipeline per check-in:
  1. Ground elevation at the office's lat/long -- via SRTM (offline after
     first tile download, no per-request cost, works anywhere on land).
  2. Current sea-level pressure near that lat/long -- via a weather API
     (needs an API key; cached per-site since weather doesn't change
     minute-to-minute).
  3. Convert #2 down to "expected pressure at this specific site's ground
     elevation" using the barometric formula.
  4. Compare the employee's raw phone barometer reading against #3.

Caveats (be upfront about these, don't oversell the accuracy):
  - Weather station is near the office, not AT it -- can be km away.
  - SRTM ground elevation has its own ~10-16m vertical error, which folds
    into the barometric conversion in step 3.
  - Net result: removes weather-drift error, does NOT remove all error.
    Realistic use: flag large discrepancies, don't hard-reject on small ones.
"""
import time
import math
import os
import requests
import srtm

OPENWEATHER_API_KEY ="b6c259ab19ce05b1699563e50ca6b85c"  # set per deployment
CACHE_TTL_SECONDS = 600  # 10 min -- weather doesn't meaningfully change faster than this

_elevation_data = srtm.get_data()  # loads/downloads tiles lazily per lookup
_pressure_cache = {}  # {(lat_rounded, lon_rounded): (timestamp, sea_level_pressure_hpa)}


def _cache_key(lat: float, lon: float):
    # Round to ~1km precision -- nearby check-ins at the same site should
    # share one cached weather lookup instead of hitting the API per request.
    return (round(lat, 2), round(lon, 2))


def get_ground_elevation(lat: float, lon: float):
    """Static, offline, per-site. Returns meters above sea level or None."""
    try:
        return _elevation_data.get_elevation(lat, lon)
    except Exception:
        return None


def get_sea_level_pressure(lat: float, lon: float):
    """Current sea-level pressure (hPa) near this lat/long, cached per-site
    to avoid hitting API rate limits when many employees check in from the
    same office within a short window."""
    key = _cache_key(lat, lon)
    cached = _pressure_cache.get(key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    if not OPENWEATHER_API_KEY:
        return None  # no key configured -- caller should treat as "unavailable"

    try:
        resp = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "appid": OPENWEATHER_API_KEY},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        pressure = data["main"]["sea_level"] if "sea_level" in data["main"] else data["main"]["pressure"]
        _pressure_cache[key] = (time.time(), pressure)
        return pressure
    except Exception as e:
        # TEMP DEBUG: print the real failure instead of swallowing it.
        # Remove this print once the root cause is found -- back to a
        # silent "unavailable" return like the rest of this app's
        # fail-open pattern.
        print(f"DEBUG: weather API call failed: {type(e).__name__}: {e}")
        return None


def sea_level_to_local_pressure(sea_level_hpa: float, elevation_m: float) -> float:
    """Barometric formula: converts sea-level pressure down to expected
    pressure at a given ground elevation."""
    return sea_level_hpa * (1 - (0.0065 * elevation_m) / 288.15) ** 5.255


def pressure_diff_to_meters(p_employee_hpa: float, p_expected_hpa: float) -> float:
    """Positive = employee reading suggests they're higher than expected ground level."""
    return 44330 * (1 - (p_employee_hpa / p_expected_hpa) ** (1 / 5.255))


def get_altitude_diff(office_lat: float, office_lon: float, employee_pressure_hpa):
    """Returns (diff_meters, note) for logging. note explains why it's None
    if any piece of the pipeline is unavailable -- always fail open (skip),
    never fail closed (reject), same pattern as the rest of this app."""
    if employee_pressure_hpa is None:
        return None, "no barometer reading from phone"

    elevation = get_ground_elevation(office_lat, office_lon)
    if elevation is None:
        return None, "SRTM elevation lookup failed"

    sea_level_pressure = get_sea_level_pressure(office_lat, office_lon)
    if sea_level_pressure is None:
        return None, "weather API unavailable or no API key configured"

    expected_local_pressure = sea_level_to_local_pressure(sea_level_pressure, elevation)
    diff_m = pressure_diff_to_meters(employee_pressure_hpa, expected_local_pressure)
    return diff_m, "ok"


if __name__ == "__main__":
    # Quick manual test -- replace with a real site's coordinates
    lat, lon = 19.2043431, 72.9700062
    test_pressure = 1008.5  # pretend phone reading
    diff, note = get_altitude_diff(lat, lon, test_pressure)
    print(f"diff_meters={diff}, note={note}")