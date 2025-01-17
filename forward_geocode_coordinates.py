#!/usr/bin/env python

"""
forward_geocode_latlong.py

Use this script to read your CSV, fill in missing latitude/longitude
rows by forward-geocoding the 'location' column, and then save back
the ENTIRE CSV with updated lat/long values.

Requires: pip install geopy
Note: Observe Nominatim usage policies if you have many rows.
"""

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

INPUT_CSV = "NorthAmericaViatorProducts_with_country.csv"
OUTPUT_CSV = "NorthAmericaViatorProducts_with_country_and_coords.csv"  # Overwrite original file (or specify a new file)

def main():
    # 1. Load the entire CSV into df
    df = pd.read_csv(INPUT_CSV)
    original_len = len(df)

    # 2. Identify rows missing lat/lon
    df_missing_coords = df[df["latitude"].isnull() | df["longitude"].isnull()].copy()
    missing_count = len(df_missing_coords)
    print(f"Found {missing_count} rows with missing coords (out of {original_len} total).")

    if missing_count == 0:
        print("No missing coords to fill. Exiting without changes.")
        return

    # 3. Initialize geocoder + rate limiter
    geolocator = Nominatim(user_agent="forward-geocode-script")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # 4. Forward-geocode each row that has missing coords
    for i, row in df_missing_coords.iterrows():
        location_str = row.get("location", None)

        # Skip if 'location' is empty or not a string
        if not isinstance(location_str, str) or not location_str.strip():
            continue

        try:
            location = geocode(location_str, language="en")
            if location:
                new_lat = location.latitude
                new_lon = location.longitude

                # Update the row in the main df
                df.at[i, "latitude"] = new_lat
                df.at[i, "longitude"] = new_lon

                print(f"[Row {i}] '{location_str}' -> lat={new_lat}, lon={new_lon}")
            else:
                print(f"[Row {i}] '{location_str}' -> No geocode result found")
        except Exception as e:
            print(f"[Row {i}] '{location_str}' -> Error: {e}")

    # 5. Save the entire df (including updated rows) back to CSV
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote updated CSV: '{OUTPUT_CSV}'")
    print("Rows with previously valid lat/lon remain intact; missing coords have been filled if found.")

if __name__ == "__main__":
    main()
