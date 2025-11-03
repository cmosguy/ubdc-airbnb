# Area of Interest (AOI) Setup Guide

This guide explains how to add and manage Areas of Interest (AOIs) in the UBDC Airbnb system. AOIs define the geographic regions where you want to collect Airbnb data.

## Table of Contents
1. [What is an AOI?](#what-is-an-aoi)
2. [Quick Start Examples](#quick-start-examples)
3. [Method 1: Using Command Line (Recommended)](#method-1-using-command-line-recommended)
4. [Method 2: Using GeoJSON Files](#method-2-using-geojson-files)
5. [Method 3: Using Python/Django Shell](#method-3-using-pythondjango-shell)
6. [Method 4: Using QGIS](#method-4-using-qgis)
7. [Managing AOIs](#managing-aois)
8. [Understanding the Grid System](#understanding-the-grid-system)
9. [Best Practices](#best-practices)

---

## What is an AOI?

An **Area of Interest (AOI)** is a geographic polygon that defines where the system should:
- 🔍 **Discover** new Airbnb listings
- 📅 **Collect** calendar availability data
- 📝 **Fetch** listing details, reviews, and booking quotes

### AOI Configuration Flags

Each AOI has boolean flags that control what data is collected:

| Flag | Purpose | Default |
|------|---------|---------|
| `scan_for_new_listings` | Discover new listings in this area | `True` |
| `collect_calendars` | Collect calendar availability | `False` |
| `collect_listing_details` | Fetch listing details | `False` |
| `collect_reviews` | Collect reviews and ratings | `False` |
| `collect_bookings` | Get booking quote information | `False` |

**Important:** After creating an AOI, you must **enable the collection flags** you want!

---

## Quick Start Examples

### Austin, TX

```bash
# Add Austin AOI
docker-compose run --rm worker add-aoi \
  --name "Austin-TX" \
  --bbox "-97.9383,30.0986,-97.5698,30.5168" \
  --description "Austin, Texas city limits"

# Enable calendar collection (get AOI ID from previous command output)
docker-compose run --rm worker edit-aoi 1 --calendars --listing-details
```

### Texas (Entire State)

```bash
# Add Texas state AOI
docker-compose run --rm worker add-aoi \
  --name "Texas-State" \
  --bbox "-106.6458,25.8371,-93.5083,36.5007" \
  --description "Texas state boundary"

# Enable collection
docker-compose run --rm worker edit-aoi 2 --calendars --listing-details
```

**Warning:** Texas is huge! Collecting data for the entire state will:
- Take **much longer** to discover listings
- Use **more API calls** (proxy costs)
- Require **more storage** in the database

Consider starting with specific cities instead.

---

## Method 1: Using Command Line (Recommended)

The easiest way to add AOIs is using the `add-aoi` management command.

### Step 1: Find Your Bounding Box Coordinates

You need a **bounding box** in this format: `minx,miny,maxx,maxy` (West, South, East, North)

**Where to get coordinates:**

1. **BoundingBox.klokantech.com** - http://boundingbox.klokantech.com/
   - Search for your location
   - Select "CSV" format
   - Copy the coordinates

2. **OpenStreetMap** - https://www.openstreetmap.org/
   - Navigate to your area
   - Click "Export"
   - Copy bounding box coordinates

3. **Manual calculation:**
   - Use Google Maps to find corners
   - Format: `west_longitude,south_latitude,east_longitude,north_latitude`

### Step 2: Add the AOI

```bash
docker-compose run --rm worker add-aoi \
  --name "YourCity" \
  --bbox "minx,miny,maxx,maxy" \
  --description "Your description here"
```

**Example: San Francisco**

```bash
docker-compose run --rm worker add-aoi \
  --name "San-Francisco" \
  --bbox "-122.5155,37.7034,-122.3549,37.8324" \
  --description "San Francisco city limits"
```

**Output:**
```
Successfully added bbox AOI "San-Francisco" (ID: 3)
Created 156 grids for AOI "San-Francisco"
```

Take note of the **ID** (you'll need it for the next step).

### Step 3: Enable Collection Flags

```bash
# Enable calendar and listing details collection
docker-compose run --rm worker edit-aoi 3 --calendars --listing-details

# Output:
# Setting collect_calendars to True for AOI 3
# Setting collect_listing_details to True for AOI 3
# Successfully updated AOI 3
```

### Step 4: Verify the AOI

```bash
docker-compose run --rm worker list-aoi

# Output:
# Found 3 AOI(s):
# --------------------------------------------------------------------------------
# ID    Name                           Created             User            Notes
# --------------------------------------------------------------------------------
# 1     Austin-TX                      2025-11-03 10:23:45 system          ...
# 2     Texas-State                    2025-11-03 10:25:12 system          ...
# 3     San-Francisco                  2025-11-03 10:30:01 system          ...
# --------------------------------------------------------------------------------
```

---

## Method 2: Using GeoJSON Files

For **complex boundaries** (irregular shapes, city limits, neighborhoods), use GeoJSON files.

### Step 1: Create a GeoJSON File

**Option A: Use geojson.io**
1. Go to https://geojson.io/
2. Draw your polygon on the map
3. Save as `austin.geojson`

**Option B: Download from OpenStreetMap**
1. Go to https://www.openstreetmap.org/
2. Search for your location
3. Use Overpass Turbo to export boundaries
4. Save as GeoJSON

**Example GeoJSON structure:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {},
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-97.9383, 30.0986],
            [-97.5698, 30.0986],
            [-97.5698, 30.5168],
            [-97.9383, 30.5168],
            [-97.9383, 30.0986]
          ]
        ]
      }
    }
  ]
}
```

### Step 2: Import the GeoJSON

```bash
# Copy GeoJSON to container (or use volume mount)
docker cp austin.geojson ubdc-airbnb-worker-1:/tmp/austin.geojson

# Import using Python shell
docker-compose run --rm worker shell

# In Python shell:
from pathlib import Path
from ubdc_airbnb.models import AOIShape

geojson_path = Path("/tmp/austin.geojson")
aoi = AOIShape.create_from_geojson(geojson_path)
aoi.name = "Austin-TX-Detailed"
aoi.save()

# Create grids for the AOI
num_grids = aoi.create_grid()
print(f"Created {num_grids} grids")

# Enable collection
aoi.collect_calendars = True
aoi.collect_listing_details = True
aoi.scan_for_new_listings = True
aoi.save()

print(f"AOI ID: {aoi.id}")
exit()
```

---

## Method 3: Using Python/Django Shell

For **programmatic control**, use the Django shell directly.

### Creating from Bounding Box

```bash
docker-compose run --rm worker shell
```

```python
from mercantile import LngLatBbox
from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.spatial import get_geom_from_bbox

# Define Austin bounding box
bbox = LngLatBbox(
    west=-97.9383,
    south=30.0986,
    east=-97.5698,
    north=30.5168
)

# Create geometry
geom = get_geom_from_bbox(bbox)
geom_3857 = geom.transform(3857, clone=True)

# Create AOI
aoi = AOIShape.objects.create(
    name="Austin-TX",
    geom_3857=geom_3857,
    notes={"description": "Austin city limits", "created_by": "python_shell"},
    scan_for_new_listings=True,
    collect_calendars=True,
    collect_listing_details=True,
)

# Create grids
num_grids = aoi.create_grid()
print(f"Created AOI {aoi.id} with {num_grids} grids")
```

### Creating from WKT (Well-Known Text)

```python
from ubdc_airbnb.models import AOIShape

# Define polygon as WKT (coordinates in EPSG:4326 / WGS84)
wkt = """POLYGON((
    -97.9383 30.0986,
    -97.5698 30.0986,
    -97.5698 30.5168,
    -97.9383 30.5168,
    -97.9383 30.0986
))"""

aoi = AOIShape.create_from_wkt(wkt, name="Austin-TX-WKT")
aoi.collect_calendars = True
aoi.save()

num_grids = aoi.create_grid()
print(f"Created AOI {aoi.id} with {num_grids} grids")
```

### Creating Multiple Cities at Once

```python
from mercantile import LngLatBbox
from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.spatial import get_geom_from_bbox

# Define cities
cities = [
    {
        "name": "Austin-TX",
        "bbox": LngLatBbox(-97.9383, 30.0986, -97.5698, 30.5168),
    },
    {
        "name": "Houston-TX",
        "bbox": LngLatBbox(-95.8236, 29.5231, -95.0139, 30.1101),
    },
    {
        "name": "Dallas-TX",
        "bbox": LngLatBbox(-97.0392, 32.6178, -96.4637, 33.0238),
    },
    {
        "name": "San-Antonio-TX",
        "bbox": LngLatBbox(-98.7000, 29.2136, -98.2950, 29.6474),
    },
]

# Create all AOIs
for city in cities:
    geom = get_geom_from_bbox(city["bbox"])
    geom_3857 = geom.transform(3857, clone=True)

    aoi = AOIShape.objects.create(
        name=city["name"],
        geom_3857=geom_3857,
        collect_calendars=True,
        collect_listing_details=True,
        scan_for_new_listings=True,
    )

    num_grids = aoi.create_grid()
    print(f"✓ Created {city['name']} (ID: {aoi.id}) with {num_grids} grids")
```

---

## Method 4: Using QGIS

For **visual boundary drawing** and **advanced GIS operations**, use QGIS.

### Prerequisites
- QGIS installed (https://qgis.org/)
- Database connection configured

### Step 1: Connect QGIS to Database

1. Open QGIS
2. **Layer** → **Add Layer** → **Add PostGIS Layers**
3. Click **New** to create connection:
   - **Name:** `ubdc-airbnb`
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `postgres`
   - **Username:** `postgres`
   - **Password:** `postgres`
4. Click **Test Connection** → Should see "Connection successful"
5. Click **OK**

### Step 2: Add Spatial Layers

1. Click **Connect** on your database connection
2. Expand the schema
3. Add these layers:
   - `app_aoishape` (AOIs)
   - `app_airbnblisting` (Listings - if any exist)
   - `app_landmask` (Land boundaries - optional)

### Step 3: Add Basemap (Optional but Recommended)

1. **Browser Panel** → Right-click **XYZ Tiles** → **New Connection**
2. **Name:** `OpenStreetMap`
3. **URL:** `http://tile.openstreetmap.org/{z}/{x}/{y}.png`
4. Click **OK**
5. Double-click `OpenStreetMap` to add to map

### Step 4: Draw Your AOI

1. Select the `app_aoishape` layer
2. Click **Toggle Editing** (pencil icon)
3. Click **Add Polygon Feature** (polygon icon)
4. Draw your polygon by clicking points
5. Right-click to finish
6. Fill in attributes:
   - **name:** `Austin-TX`
   - **scan_for_new_listings:** `1` (true)
   - **collect_calendars:** `1` (true)
   - **collect_listing_details:** `1` (true)
   - **collect_reviews:** `0` (false)
   - **collect_bookings:** `0` (false)
7. Click **OK**
8. Click **Save Layer Edits**
9. Note the AOI ID in the attribute table

### Step 5: Create Grids (Required!)

After drawing in QGIS, you **must** create grids:

```bash
# If your AOI ID is 5
docker-compose run --rm worker shell

# In Python:
from ubdc_airbnb.models import AOIShape
aoi = AOIShape.objects.get(id=5)
num_grids = aoi.create_grid()
print(f"Created {num_grids} grids for {aoi.name}")
exit()
```

---

## Managing AOIs

### List All AOIs

```bash
docker-compose run --rm worker list-aoi
```

### Filter AOIs by Name

```bash
docker-compose run --rm worker list-aoi --filter "Austin"
```

### Export AOIs to CSV

```bash
docker-compose run --rm worker list-aoi --csv --output aois.csv
```

### Enable Collection Flags

```bash
# Enable calendars
docker-compose run --rm worker edit-aoi 1 --calendars

# Disable calendars
docker-compose run --rm worker edit-aoi 1 --no-calendars

# Enable listing details
docker-compose run --rm worker edit-aoi 1 --listing-details

# Enable both at once
docker-compose run --rm worker edit-aoi 1 --calendars --listing-details
```

### Delete an AOI

```bash
docker-compose run --rm worker edit-aoi 1 --delete
```

### Check AOI Status in Database

```bash
docker-compose run --rm worker shell

# In Python:
from ubdc_airbnb.models import AOIShape

# Get all AOIs
aois = AOIShape.objects.all()
for aoi in aois:
    print(f"ID: {aoi.id}")
    print(f"  Name: {aoi.name}")
    print(f"  Calendars: {aoi.collect_calendars}")
    print(f"  Details: {aoi.collect_listing_details}")
    print(f"  Listings: {aoi.listings.count()}")
    print()
```

---

## Understanding the Grid System

### What are Grids?

The system uses a **quadkey-based grid system** to:
- Divide large areas into manageable search tiles
- Handle Airbnb's 300 listing limit per search
- Efficiently discover all listings in an area

### How Grids Work

```
┌────────────────────────────────────────────────────────────┐
│                    Your AOI (Austin)                       │
│                                                            │
│  ┌──────┬──────┬──────┬──────┐                            │
│  │ Grid │ Grid │ Grid │ Grid │  Each grid is a search     │
│  │  1   │  2   │  3   │  4   │  query to Airbnb API       │
│  ├──────┼──────┼──────┼──────┤                            │
│  │ Grid │ Grid │ Grid │ Grid │  If a grid has >50         │
│  │  5   │  6   │  7   │  8   │  listings, it subdivides   │
│  ├──────┼──────┼──────┼──────┤  into 4 smaller grids      │
│  │ Grid │ Grid │ Grid │ Grid │                            │
│  │  9   │  10  │  11  │  12  │  This continues until all  │
│  ├──────┼──────┼──────┼──────┤  grids have <50 listings   │
│  │ Grid │ Grid │ Grid │ Grid │                            │
│  │  13  │  14  │  15  │  16  │                            │
│  └──────┴──────┴──────┴──────┘                            │
└────────────────────────────────────────────────────────────┘
```

### Grid Creation Process

When you create an AOI, `create_grid()`:

1. **Divides** the AOI into initial tiles (quadkeys)
2. **Handles** prime meridian crossings automatically
3. **Creates** `UBDCGrid` records in database
4. **Returns** the number of grids created

**Example:**
```
Austin AOI → 156 grids
Texas State → ~12,000 grids (!)
San Francisco → 89 grids
```

### Grid Discovery Process

After creating grids, run **listing discovery**:

```bash
docker-compose run --rm worker find-listings <AOI-ID>
```

This will:
1. Query each grid to count listings
2. If grid has >50 listings, subdivide it
3. Continue recursively until all grids have <50 listings
4. Store discovered listing IDs in database

---

## Best Practices

### 1. Start Small

❌ **Don't do this first:**
```bash
# Entire Texas - 268,596 sq mi - will take days/weeks!
docker-compose run --rm worker add-aoi --name "Texas" --bbox "-106.6458,25.8371,-93.5083,36.5007"
```

✅ **Do this instead:**
```bash
# Single city - manageable in hours
docker-compose run --rm worker add-aoi --name "Austin-Downtown" --bbox "-97.7654,30.2515,-97.7183,30.2838"
```

### 2. Use Meaningful Names

✅ **Good names:**
- `Austin-TX-Downtown`
- `Glasgow-City-Centre`
- `Paris-Arrondissements-1-4`

❌ **Bad names:**
- `test123`
- `aoi`
- `NewAOI`

### 3. Document Your AOIs

Use the `notes` field to add metadata:

```python
aoi.notes = {
    "description": "Austin city limits",
    "created_by": "john@example.com",
    "purpose": "Q4 2025 market analysis",
    "date_added": "2025-11-03",
}
aoi.save()
```

### 4. Enable Only What You Need

Each collection type uses API calls (costs money via proxy):

```bash
# If you only need calendars, don't enable everything
docker-compose run --rm worker edit-aoi 1 --calendars  # ✓
# Not: --calendars --listing-details --reviews  # ✗ (wastes API calls)
```

### 5. Monitor Your First Discovery

Watch the first discovery run to estimate time:

```bash
# Start discovery
docker-compose run --rm worker find-listings 1

# In another terminal, watch progress
docker-compose logs -f worker
```

### 6. Use GeoJSON for Complex Boundaries

For **actual city limits** (not just rectangles), use GeoJSON:

**Sources:**
- https://osm-boundaries.com/
- https://data.cityofaustin.org/ (Austin specific)
- https://www.census.gov/geographies/mapping-files.html (US Census)

### 7. Consider Area Size vs. Listing Density

**Small dense area:** Quick discovery, many listings
- Example: Manhattan - 23 sq mi, ~20,000 listings

**Large sparse area:** Slow discovery, few listings
- Example: Rural Texas - 1,000 sq mi, ~50 listings

**Recommendation:** Focus on cities and tourist destinations.

---

## Common Bounding Boxes

Here are some ready-to-use bounding boxes for major US cities:

```bash
# Austin, TX
-97.9383,30.0986,-97.5698,30.5168

# Houston, TX
-95.8236,29.5231,-95.0139,30.1101

# Dallas, TX
-97.0392,32.6178,-96.4637,33.0238

# San Antonio, TX
-98.7000,29.2136,-98.2950,29.6474

# New York, NY
-74.2591,40.4774,-73.7004,40.9176

# Los Angeles, CA
-118.6682,33.7037,-118.1553,34.3373

# San Francisco, CA
-122.5155,37.7034,-122.3549,37.8324

# Chicago, IL
-87.9401,41.6445,-87.5241,42.0230

# Seattle, WA
-122.4598,47.4810,-122.2244,47.7341

# Miami, FL
-80.3203,25.7090,-80.1300,25.8557
```

---

## Complete Example: Setting Up Austin, TX

Here's a complete workflow from start to finish:

```bash
# 1. Add the AOI
docker-compose run --rm worker add-aoi \
  --name "Austin-TX" \
  --bbox "-97.9383,30.0986,-97.5698,30.5168" \
  --description "Austin, Texas city limits for Q4 2025 analysis"

# Output: Successfully added bbox AOI "Austin-TX" (ID: 1)
#         Created 156 grids for AOI "Austin-TX"

# 2. Enable collection
docker-compose run --rm worker edit-aoi 1 --calendars --listing-details

# 3. Verify
docker-compose run --rm worker list-aoi

# 4. Discover listings
docker-compose run --rm worker find-listings 1

# This will take time! For Austin: ~30-60 minutes depending on workers
# It will discover ~8,000-12,000 listings

# 5. Check progress in another terminal
docker-compose logs -f worker | grep "Listing:"

# 6. When discovery completes, verify
docker-compose run --rm worker shell

# In Python:
from ubdc_airbnb.models import AOIShape
aoi = AOIShape.objects.get(id=1)
print(f"AOI: {aoi.name}")
print(f"Listings found: {aoi.listings.count()}")
exit()

# 7. Calendar collection will now run automatically at 2 AM daily!
# Or trigger manually:
docker-compose run --rm worker send-task op_update_calendar_at_aoi --kwargs '{"id_shape": 1}'
```

---

## Troubleshooting

### "No grids created for AOI"

**Problem:** Grids weren't automatically created

**Solution:**
```bash
docker-compose run --rm worker shell

from ubdc_airbnb.models import AOIShape
aoi = AOIShape.objects.get(id=YOUR_AOI_ID)
num_grids = aoi.create_grid()
print(f"Created {num_grids} grids")
```

### "No listings found"

**Possible causes:**
1. Grids not created → See above
2. AOI is in the ocean → Check coordinates
3. Airbnb has no listings there → Try a different area
4. Proxy issues → Check proxy configuration

### "Geometry error when creating AOI"

**Problem:** Invalid coordinates or crossing date line

**Solution:**
- Verify coordinates are in correct order: `minx,miny,maxx,maxy`
- Ensure coordinates are in WGS84 (EPSG:4326)
- Check that west < east and south < north

### "Collection not happening"

**Checklist:**
1. Are collection flags enabled? `edit-aoi X --calendars`
2. Are there listings in the AOI? `aoi.listings.count()`
3. Is Celery Beat running? `docker ps | grep beat`
4. Check logs: `docker-compose logs beat`

---

## Next Steps

After setting up your AOI:

1. **Discover Listings:** Run `find-listings <AOI-ID>` to populate the database
2. **Monitor Progress:** Watch logs and check listing counts
3. **Enable Scheduling:** Celery Beat will automatically collect data daily
4. **Analyze Data:** Query the database for insights

For more information:
- **Calendar Collection:** See `CALENDAR_COLLECTION_GUIDE.md`
- **Proxy Setup:** See `PROXY_MIGRATION_GUIDE.md`
- **Operations:** See `README/setup.md`

---

## Summary Commands

```bash
# Add AOI
docker-compose run --rm worker add-aoi --name "YourCity" --bbox "minx,miny,maxx,maxy"

# Enable collection
docker-compose run --rm worker edit-aoi <ID> --calendars --listing-details

# List AOIs
docker-compose run --rm worker list-aoi

# Discover listings
docker-compose run --rm worker find-listings <AOI-ID>

# Check status
docker-compose run --rm worker shell
# Then: AOIShape.objects.get(id=X).listings.count()
```

Happy mapping! 🗺️
