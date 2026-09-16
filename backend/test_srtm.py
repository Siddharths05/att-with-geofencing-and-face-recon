"""
Test srtm.py (offline elevation lookup, no API key needed) with your
actual office coordinates.

First run: pip install srtm.py
Then:      python test_srtm.py

First call downloads the relevant SRTM tile (a few MB) and caches it --
needs internet ONCE, then works offline after that.
"""
import srtm

OFFICE_LAT = 19.2043431
OFFICE_LON = 72.9700062

if __name__ == "__main__":
    print(f"Looking up elevation for ({OFFICE_LAT}, {OFFICE_LON})...")
    elevation_data = srtm.get_data()
    elevation = elevation_data.get_elevation(OFFICE_LAT, OFFICE_LON)

    if elevation is None:
        print("No data returned -- coordinates might be outside SRTM coverage"
              " (SRTM covers roughly 60N to 56S, so this is unlikely for India,"
              " but possible over large water bodies).")
    else:
        print(f"Ground elevation: {elevation} meters above sea level")
