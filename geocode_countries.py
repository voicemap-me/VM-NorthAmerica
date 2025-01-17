#!/usr/bin/env python

"""
geocode_countries.py

Use this script to read 'NorthAmericaViatorProducts.csv',
reverse-geocode the latitude/longitude, and produce a new CSV
with a 'country' column. Then your Streamlit app can read
this new CSV without performing geocoding in real-time.
"""

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

INPUT_CSV = "NorthAmericaViatorProducts.csv"
OUTPUT_CSV = "NorthAmericaViatorProducts_with_country.csv"

def main():
    # 1. Load your CSV
    df = pd.read_csv(INPUT_CSV)

    # 2. Initialize geocoder + rate limiter
    geolocator = Nominatim(user_agent="offline-geocode-script")
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1) 
    # -> 1 second between calls to avoid rate limit

    # 3. Prepare a 'country' column to fill
    df["country"] = None  # or "Unknown"

    # 4. Reverse Geocode each row that has lat/lon
    for i, row in df.iterrows():
        lat = row.get("latitude", None)
        lon = row.get("longitude", None)

        # Skip if lat/lon is missing or already have a country
        if pd.isna(lat) or pd.isna(lon):
            df.at[i, "country"] = "Unknown"
            continue

        try:
            location = reverse((lat, lon), language="en")
            if location and "address" in location.raw:
                addr = location.raw["address"]
                country_name = addr.get("country", "Unknown")
            else:
                country_name = "Unknown"
        except Exception as e:
            country_name = "Unknown"

        df.at[i, "country"] = country_name

        # (Optional) Print progress
        print(f"{i+1}/{len(df)}: lat={lat}, lon={lon} -> {country_name}")
    
    # 5. Save to new CSV
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nDone! Wrote '{OUTPUT_CSV}' with country column.")


if __name__ == "__main__":
    main()
