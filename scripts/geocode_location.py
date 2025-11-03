#!/usr/bin/env python3
"""
Standalone script to geocode locations and get bounding boxes.

This script can be run outside of Django to quickly look up coordinates.

Usage:
    python geocode_location.py "Austin, Texas"
    python geocode_location.py "London, UK"
    python geocode_location.py "Paris, France" --country fr
    python geocode_location.py --batch cities.txt
"""

import argparse
import sys
import time
from typing import Optional, Tuple

import requests


def geocode_nominatim(
    query: str,
    country: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Geocode using Nominatim API.

    Args:
        query: Location name
        country: Optional 2-letter country code

    Returns:
        Tuple of (display_name, bbox_string)
    """
    url = "https://nominatim.openstreetmap.org/search"

    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }

    if country:
        params["countrycodes"] = country

    headers = {
        "User-Agent": "UBDC-Airbnb-Research/1.0",
    }

    try:
        # Rate limiting (1 req/sec for Nominatim)
        time.sleep(1)

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        results = response.json()

        if not results:
            raise ValueError(f"Location not found: {query}")

        result = results[0]
        bbox = result.get("boundingbox")

        if not bbox or len(bbox) != 4:
            raise ValueError(f"Invalid bbox in response")

        # Nominatim returns: [min_lat, max_lat, min_lon, max_lon]
        # Convert to: [min_lon, min_lat, max_lon, max_lat]
        min_lat, max_lat, min_lon, max_lon = map(float, bbox)
        bbox_string = f"{min_lon},{min_lat},{max_lon},{max_lat}"

        display_name = result.get("display_name", query)

        return (display_name, bbox_string)

    except requests.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Geocode locations and get bounding boxes"
    )
    parser.add_argument(
        "location",
        nargs="?",
        help='Location to geocode (e.g., "Austin, Texas")',
    )
    parser.add_argument(
        "--country",
        help="2-letter country code (e.g., us, gb, fr)",
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="Batch geocode locations from a file (one per line)",
    )
    parser.add_argument(
        "--format",
        choices=["human", "csv", "json"],
        default="human",
        help="Output format (default: human)",
    )

    args = parser.parse_args()

    # Batch mode
    if args.batch:
        try:
            with open(args.batch, "r") as f:
                locations = [line.strip() for line in f if line.strip()]
        except IOError as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

        results = []
        for location in locations:
            try:
                name, bbox = geocode_nominatim(location, args.country)
                results.append((location, name, bbox, "OK"))
            except Exception as e:
                results.append((location, None, None, str(e)))

        # Output results
        if args.format == "csv":
            print("query,display_name,bbox,status")
            for query, name, bbox, status in results:
                print(f'"{query}","{name}","{bbox}","{status}"')
        elif args.format == "json":
            import json

            output = [
                {
                    "query": q,
                    "display_name": n,
                    "bbox": b,
                    "status": s,
                }
                for q, n, b, s in results
            ]
            print(json.dumps(output, indent=2))
        else:
            for query, name, bbox, status in results:
                if bbox:
                    print(f"✓ {query}")
                    print(f"  Name: {name}")
                    print(f"  Bbox: {bbox}")
                else:
                    print(f"✗ {query}: {status}")
                print()

        return

    # Single location mode
    if not args.location:
        parser.print_help()
        sys.exit(1)

    try:
        display_name, bbox_string = geocode_nominatim(args.location, args.country)

        if args.format == "csv":
            print("display_name,bbox")
            print(f'"{display_name}","{bbox_string}"')
        elif args.format == "json":
            import json

            output = {
                "query": args.location,
                "display_name": display_name,
                "bbox": bbox_string,
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"Location: {display_name}")
            print(f"Bbox:     {bbox_string}")
            print()
            print("To create an AOI:")
            print(
                f'docker-compose run --rm worker add-aoi --name "YourName" --bbox "{bbox_string}"'
            )

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
