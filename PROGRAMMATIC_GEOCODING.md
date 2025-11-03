# Programmatic Geocoding - API Guide

This guide shows you how to get bounding box coordinates **programmatically** using free APIs and Python, without needing to manually look up coordinates.

## Table of Contents
1. [Quick Start](#quick-start)
2. [Using the Management Command](#using-the-management-command)
3. [Using Python Directly](#using-python-directly)
4. [Standalone Script](#standalone-script)
5. [Free APIs Available](#free-apis-available)
6. [Batch Geocoding](#batch-geocoding)
7. [API Reference](#api-reference)

---

## Quick Start

### The Easiest Way: Use the New Command!

Instead of looking up coordinates manually, just use the location name:

```bash
# Old way (manual lookup required):
docker-compose run --rm worker add-aoi --name "Austin-TX" --bbox "-97.9383,30.0986,-97.5698,30.5168"

# New way (automatic lookup!):
docker-compose run --rm worker add-aoi-by-name "Austin, Texas"
```

**That's it!** The system will:
1. Query the Nominatim API (free, no key required)
2. Find the bounding box automatically
3. Create the AOI with proper coordinates
4. Generate grids
5. Show you next steps

---

## Using the Management Command

### Basic Usage

```bash
# US Cities
docker-compose run --rm worker add-aoi-by-name "Austin, Texas"
docker-compose run --rm worker add-aoi-by-name "Houston, Texas"
docker-compose run --rm worker add-aoi-by-name "New York City"

# International Cities
docker-compose run --rm worker add-aoi-by-name "London, UK"
docker-compose run --rm worker add-aoi-by-name "Paris, France"
docker-compose run --rm worker add-aoi-by-name "Tokyo, Japan"

# States/Provinces
docker-compose run --rm worker add-aoi-by-name "Texas"
docker-compose run --rm worker add-aoi-by-name "California"
```

### Example Output

```bash
$ docker-compose run --rm worker add-aoi-by-name "Austin, Texas"

🔍 Searching for: Austin, Texas
✓ Found: Austin, Travis County, Texas, United States
  Bounding box: -97.9383,30.0986,-97.5698,30.5168

📊 AOI Details:
  Name: Austin
  Location: Austin, Travis County, Texas, United States
  Bbox: -97.9383,30.0986,-97.5698,30.5168
  Area: ~1,285 sq km

🔨 Creating grids...
✓ Successfully created AOI "Austin" (ID: 1)
✓ Created 156 grids for AOI "Austin"

✨ Next steps:
   1. Enable collection: edit-aoi 1 --calendars --listing-details
   2. Discover listings: find-listings 1
   3. View status: list-aoi
```

### Advanced Options

```bash
# Custom name
docker-compose run --rm worker add-aoi-by-name "Austin, Texas" --name "Austin-Downtown"

# Specify country to narrow search
docker-compose run --rm worker add-aoi-by-name "Paris" --country fr

# Use alternative provider (Photon)
docker-compose run --rm worker add-aoi-by-name "London" --provider photon

# Preview without creating (dry run)
docker-compose run --rm worker add-aoi-by-name "Texas" --dry-run

# Don't use cached results
docker-compose run --rm worker add-aoi-by-name "Austin" --no-cache
```

---

## Using Python Directly

You can also use the geocoding functions in your own Python code.

### In Django Shell

```bash
docker-compose run --rm worker shell
```

```python
from ubdc_airbnb.utils.geocoding import geocode_and_format, geocode_city, geocode_state

# Basic geocoding
name, bbox = geocode_and_format("Austin, Texas")
print(f"{name}: {bbox}")
# Output: Austin, Travis County, Texas, United States: -97.9383,30.0986,-97.5698,30.5168

# Geocode a US city
name, bbox = geocode_city("Austin", "Texas")
print(bbox)
# Output: -97.9383,30.0986,-97.5698,30.5168

# Geocode a US state
name, bbox = geocode_state("Texas")
print(bbox)
# Output: -106.6458,25.8371,-93.5083,36.5007

# Now create AOI with the result
from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.spatial import get_geom_from_bbox
from mercantile import LngLatBbox

west, south, east, north = map(float, bbox.split(","))
geom = get_geom_from_bbox(LngLatBbox(west, south, east, north))
geom_3857 = geom.transform(3857, clone=True)

aoi = AOIShape.objects.create(
    name="Austin-TX",
    geom_3857=geom_3857,
    collect_calendars=True,
    collect_listing_details=True,
)
num_grids = aoi.create_grid()
print(f"Created AOI {aoi.id} with {num_grids} grids")
```

### Batch Geocoding Multiple Cities

```python
from ubdc_airbnb.utils.geocoding import batch_geocode

# List of cities to geocode
cities = [
    "Austin, Texas",
    "Houston, Texas",
    "Dallas, Texas",
    "San Antonio, Texas",
]

# Geocode all at once (respects rate limiting)
results = batch_geocode(cities)

# Create AOIs for all
from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.spatial import get_geom_from_bbox
from mercantile import LngLatBbox

for query, (name, bbox) in results.items():
    if bbox:
        west, south, east, north = map(float, bbox.split(","))
        geom = get_geom_from_bbox(LngLatBbox(west, south, east, north))
        geom_3857 = geom.transform(3857, clone=True)

        aoi_name = name.split(",")[0].strip().replace(" ", "-")
        aoi = AOIShape.objects.create(
            name=aoi_name,
            geom_3857=geom_3857,
            collect_calendars=True,
            collect_listing_details=True,
        )
        num_grids = aoi.create_grid()
        print(f"✓ {aoi_name}: ID={aoi.id}, Grids={num_grids}")
```

---

## Standalone Script

For quick lookups **outside of Docker**, use the standalone script:

### Installation

```bash
pip install requests
```

### Usage

```bash
# Single location
python scripts/geocode_location.py "Austin, Texas"

# Output:
# Location: Austin, Travis County, Texas, United States
# Bbox:     -97.9383,30.0986,-97.5698,30.5168
#
# To create an AOI:
# docker-compose run --rm worker add-aoi --name "YourName" --bbox "-97.9383,30.0986,-97.5698,30.5168"

# With country filter
python scripts/geocode_location.py "Paris" --country fr

# CSV output
python scripts/geocode_location.py "Austin, Texas" --format csv

# JSON output
python scripts/geocode_location.py "Austin, Texas" --format json
```

### Batch Processing

Create a file with locations (one per line):

```bash
# cities.txt
Austin, Texas
Houston, Texas
Dallas, Texas
San Antonio, Texas
Fort Worth, Texas
```

Run batch geocoding:

```bash
python scripts/geocode_location.py --batch cities.txt

# CSV output
python scripts/geocode_location.py --batch cities.txt --format csv > results.csv

# JSON output
python scripts/geocode_location.py --batch cities.txt --format json > results.json
```

---

## Free APIs Available

### 1. Nominatim (OpenStreetMap) - **Default**

**Best for:** Most use cases, accurate, worldwide coverage

**Features:**
- ✅ Free, no API key required
- ✅ Based on OpenStreetMap data
- ✅ Worldwide coverage
- ✅ Returns official boundaries
- ✅ Results cached for 24 hours

**Limitations:**
- 🔸 Rate limit: 1 request per second
- 🔸 Max 1 concurrent connection
- 🔸 Must provide User-Agent

**Usage:**
```bash
docker-compose run --rm worker add-aoi-by-name "Austin, Texas" --provider nominatim
```

**API Endpoint:**
```
https://nominatim.openstreetmap.org/search
```

**Example Request:**
```python
import requests

url = "https://nominatim.openstreetmap.org/search"
params = {
    "q": "Austin, Texas",
    "format": "json",
    "limit": 1,
}
headers = {
    "User-Agent": "YourApp/1.0"
}

response = requests.get(url, params=params, headers=headers)
result = response.json()[0]
bbox = result["boundingbox"]  # [min_lat, max_lat, min_lon, max_lon]
```

### 2. Photon - **Alternative**

**Best for:** Faster responses, no rate limiting

**Features:**
- ✅ Free, no API key required
- ✅ Based on OpenStreetMap data
- ✅ Fast responses
- ✅ No strict rate limiting

**Limitations:**
- 🔸 Doesn't return bounding boxes (creates small buffer around point)
- 🔸 Less accurate for large areas

**Usage:**
```bash
docker-compose run --rm worker add-aoi-by-name "Austin, Texas" --provider photon
```

**API Endpoint:**
```
https://photon.komoot.io/api/
```

### 3. Other Options (Require API Keys)

**Google Geocoding API:**
- Requires API key
- Free tier: 40,000 requests/month
- Very accurate
- https://developers.google.com/maps/documentation/geocoding

**Mapbox Geocoding API:**
- Requires API key
- Free tier: 100,000 requests/month
- Fast and accurate
- https://docs.mapbox.com/api/search/geocoding/

**OpenCage Geocoding API:**
- Requires API key
- Free tier: 2,500 requests/day
- Simple to use
- https://opencagedata.com/api

---

## Batch Geocoding

### Using Python Function

```python
from ubdc_airbnb.utils.geocoding import batch_geocode

# Define your locations
locations = [
    "Austin, Texas",
    "Houston, Texas",
    "Dallas, Texas",
    "San Antonio, Texas",
    "Fort Worth, Texas",
    "El Paso, Texas",
]

# Geocode all (1 second delay between requests)
results = batch_geocode(locations, delay=1.0)

# Process results
for location, (name, bbox) in results.items():
    if bbox:
        print(f"✓ {location}: {bbox}")
    else:
        print(f"✗ {location}: Not found")
```

### Using Standalone Script

```bash
# Create file with locations
cat > texas_cities.txt << EOF
Austin, Texas
Houston, Texas
Dallas, Texas
San Antonio, Texas
Fort Worth, Texas
El Paso, Texas
EOF

# Geocode all
python scripts/geocode_location.py --batch texas_cities.txt --format csv > texas_results.csv

# View results
cat texas_results.csv
```

### Creating AOIs from Batch Results

```python
import csv
from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.spatial import get_geom_from_bbox
from mercantile import LngLatBbox

# Read CSV results
with open("texas_results.csv") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["status"] != "OK":
            continue

        bbox_string = row["bbox"]
        west, south, east, north = map(float, bbox_string.split(","))

        geom = get_geom_from_bbox(LngLatBbox(west, south, east, north))
        geom_3857 = geom.transform(3857, clone=True)

        # Clean up name
        aoi_name = row["query"].replace(", ", "-").replace(" ", "-")

        aoi = AOIShape.objects.create(
            name=aoi_name,
            geom_3857=geom_3857,
            collect_calendars=True,
            collect_listing_details=True,
            notes={"geocoded_from": row["query"]},
        )

        num_grids = aoi.create_grid()
        print(f"✓ {aoi_name}: ID={aoi.id}, Grids={num_grids}")
```

---

## API Reference

### `geocode_location(query, provider, country, cache_results)`

Main geocoding function.

**Parameters:**
- `query` (str): Location name (e.g., "Austin, Texas")
- `provider` (str): API provider ("nominatim" or "photon")
- `country` (str, optional): 2-letter country code (e.g., "us", "gb")
- `cache_results` (bool): Whether to cache (default: True, 24hr TTL)

**Returns:**
- Tuple: `(display_name, west, south, east, north)`

**Example:**
```python
from ubdc_airbnb.utils.geocoding import geocode_location

name, w, s, e, n = geocode_location("Austin, Texas")
print(f"{name}: {w},{s},{e},{n}")
```

---

### `geocode_and_format(query, **kwargs)`

Geocode and return formatted bbox string.

**Parameters:**
- `query` (str): Location name
- `**kwargs`: Additional parameters for `geocode_location()`

**Returns:**
- Tuple: `(display_name, bbox_string)`

**Example:**
```python
from ubdc_airbnb.utils.geocoding import geocode_and_format

name, bbox = geocode_and_format("Austin, Texas")
print(f"{name}: {bbox}")
# Austin, Travis County, Texas: -97.9383,30.0986,-97.5698,30.5168
```

---

### `geocode_city(city, state, country)`

Convenience function for US cities.

**Parameters:**
- `city` (str): City name
- `state` (str, optional): State name or abbreviation
- `country` (str): Country code (default: "us")

**Returns:**
- Tuple: `(display_name, bbox_string)`

**Example:**
```python
from ubdc_airbnb.utils.geocoding import geocode_city

name, bbox = geocode_city("Austin", "Texas")
name, bbox = geocode_city("Austin", "TX")
```

---

### `geocode_state(state, country)`

Convenience function for US states.

**Parameters:**
- `state` (str): State name or abbreviation
- `country` (str): Country code (default: "us")

**Returns:**
- Tuple: `(display_name, bbox_string)`

**Example:**
```python
from ubdc_airbnb.utils.geocoding import geocode_state

name, bbox = geocode_state("Texas")
name, bbox = geocode_state("TX")
```

---

### `batch_geocode(locations, delay, **kwargs)`

Geocode multiple locations with rate limiting.

**Parameters:**
- `locations` (list): List of location names
- `delay` (float): Delay between requests in seconds (default: 1.0)
- `**kwargs`: Additional parameters for `geocode_location()`

**Returns:**
- dict: Mapping of location to `(display_name, bbox_string)`

**Example:**
```python
from ubdc_airbnb.utils.geocoding import batch_geocode

cities = ["Austin, TX", "Houston, TX", "Dallas, TX"]
results = batch_geocode(cities)

for city, (name, bbox) in results.items():
    print(f"{city} -> {bbox}")
```

---

## Error Handling

### Location Not Found

```python
from ubdc_airbnb.utils.geocoding import geocode_and_format, LocationNotFoundError

try:
    name, bbox = geocode_and_format("Nonexistent City")
except LocationNotFoundError as e:
    print(f"Error: {e}")
    # Try with more specific query
    name, bbox = geocode_and_format("Nonexistent City, State, Country")
```

### API Errors

```python
from ubdc_airbnb.utils.geocoding import geocode_and_format, GeocodingAPIError

try:
    name, bbox = geocode_and_format("Austin, Texas")
except GeocodingAPIError as e:
    print(f"API Error: {e}")
    # Maybe try different provider
    name, bbox = geocode_and_format("Austin, Texas", provider="photon")
```

---

## Best Practices

### 1. Use Caching

Results are automatically cached for 24 hours. Don't disable unless necessary:

```python
# Good - uses cache
geocode_and_format("Austin, Texas")

# Avoid - bypasses cache
geocode_and_format("Austin, Texas", cache_results=False)
```

### 2. Respect Rate Limits

Nominatim has a 1 req/second limit. Use `batch_geocode()` which handles this:

```python
# Good - automatic rate limiting
results = batch_geocode(many_cities)

# Avoid - manual loop without delays
for city in many_cities:
    geocode_and_format(city)  # Will get rate limited!
```

### 3. Be Specific

More specific queries = better results:

```bash
# Ambiguous
add-aoi-by-name "Portland"

# Better
add-aoi-by-name "Portland, Oregon"
add-aoi-by-name "Portland" --country us

# Best
add-aoi-by-name "Portland, Oregon, USA"
```

### 4. Use Country Codes

For non-US locations, specify country:

```bash
# Ambiguous
add-aoi-by-name "Paris"

# Clear
add-aoi-by-name "Paris" --country fr
add-aoi-by-name "Paris, France"
```

### 5. Verify Large Areas

Always use `--dry-run` for states/countries:

```bash
# Check first
add-aoi-by-name "Texas" --dry-run

# Then create
add-aoi-by-name "Texas"
```

---

## Complete Examples

### Example 1: Create Multiple Texas Cities

```bash
#!/bin/bash
# create_texas_cities.sh

cities=(
    "Austin, Texas"
    "Houston, Texas"
    "Dallas, Texas"
    "San Antonio, Texas"
    "Fort Worth, Texas"
)

for city in "${cities[@]}"; do
    echo "Creating AOI for: $city"
    docker-compose run --rm worker add-aoi-by-name "$city"
    echo ""
done
```

### Example 2: International Cities

```python
# international_aois.py
from ubdc_airbnb.utils.geocoding import batch_geocode
from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.spatial import get_geom_from_bbox
from mercantile import LngLatBbox

cities = [
    "London, UK",
    "Paris, France",
    "Berlin, Germany",
    "Tokyo, Japan",
    "Sydney, Australia",
]

results = batch_geocode(cities)

for query, (name, bbox) in results.items():
    if not bbox:
        print(f"✗ Skipping {query} - not found")
        continue

    west, south, east, north = map(float, bbox.split(","))
    geom = get_geom_from_bbox(LngLatBbox(west, south, east, north))
    geom_3857 = geom.transform(3857, clone=True)

    aoi_name = name.split(",")[0].strip()
    aoi = AOIShape.objects.create(
        name=aoi_name,
        geom_3857=geom_3857,
        collect_calendars=True,
        notes={"geocoded_from": query},
    )

    num_grids = aoi.create_grid()
    print(f"✓ {aoi_name}: ID={aoi.id}, Grids={num_grids}")
```

### Example 3: US States

```bash
# State by state setup
for state in Texas California Florida "New York"; do
    docker-compose run --rm worker add-aoi-by-name "$state" --country us --dry-run
done

# After reviewing dry-run output, create them
for state in Texas California Florida "New York"; do
    docker-compose run --rm worker add-aoi-by-name "$state" --country us
done
```

---

## Troubleshooting

### "Location not found"

**Try:**
1. Add more specificity: "Austin, Texas, USA"
2. Use country code: `--country us`
3. Try alternative spelling
4. Check OpenStreetMap to see if location exists

### "Rate limited"

**Solution:**
Use `batch_geocode()` which automatically handles delays:
```python
results = batch_geocode(cities, delay=1.5)  # 1.5 sec between requests
```

### "Invalid bounding box"

**Likely causes:**
1. Location is a point (no area)
2. API returned unexpected format
3. Use Nominatim instead of Photon

---

## Summary

**Easiest way:**
```bash
docker-compose run --rm worker add-aoi-by-name "Austin, Texas"
```

**Python way:**
```python
from ubdc_airbnb.utils.geocoding import geocode_and_format
name, bbox = geocode_and_format("Austin, Texas")
```

**Standalone way:**
```bash
python scripts/geocode_location.py "Austin, Texas"
```

**No more manual coordinate lookup needed!** 🎉
