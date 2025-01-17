#!/usr/bin/env python

"""
update_unknown_countries.py

Use this script to read "NorthAmericaViatorProducts.csv" (or your
desired CSV), and update the 'country' column ONLY where it's
currently "Unknown" by reverse-geocoding the latitude/longitude.

It saves back to the same CSV (or a new one) with updated country
values if geocoding is successful.

Requires: pip install geopy

Be sure to comply with Nominatim usage policies if you have many rows.
"""

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

INPUT_CSV = "NorthAmericaViatorProducts_with_country_and_coords.csv"
OUTPUT_CSV = "NorthAmericaViatorProducts_with_country_and_coords_full.csv"  # Overwrite existing file, or set a new name

def main():
    # 1. Load your CSV
    df = pd.read_csv(INPUT_CSV)
    original_len = len(df)
    
    # 2. Identify rows where country == "Unknown"
    df_missing_country = df[df["country"] == "Unknown"].copy()
    missing_count = len(df_missing_country)
    print(f"Found {missing_count} rows with 'Unknown' country (out of {original_len} total).")

    if missing_count == 0:
        print("No 'Unknown' countries to update. Exiting.")
        return

    # 3. Initialize geocoder + rate limiter
    geolocator = Nominatim(user_agent="update-unknown-countries-script")
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)
    # -> 1 query per second to avoid rate-limits on Nominatim

    # 4. Loop over rows with 'Unknown' country; fill if lat/lon is valid
    for i, row in df_missing_country.iterrows():
        lat = row.get("latitude", None)
        lon = row.get("longitude", None)
        
        if pd.isna(lat) or pd.isna(lon):
            # If there's no lat/lon for this row, we can't do reverse geocoding
            # We'll leave it as "Unknown"
            continue

        try:
            location = reverse((lat, lon), language="en")
            if location and "address" in location.raw:
                addr = location.raw["address"]
                country_name = addr.get("country", "Unknown")
            else:
                country_name = "Unknown"
        except Exception as e:
            print(f"[Row {i}] Reverse geocode error: {e}")
            country_name = "Unknown"

        # Update the country in the original df
        df.at[i, "country"] = country_name
        print(f"[Row {i}] lat={lat}, lon={lon} -> country={country_name}")

    # 5. Save the entire df (including updated rows) back to CSV
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nWrote updated CSV: '{OUTPUT_CSV}'.")
    print("Only rows that had 'Unknown' country were modified (if lat/lon was valid).")

if __name__ == "__main__":
    main()
