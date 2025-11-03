# Finding Bounding Box Coordinates - Practical Guide

This guide shows you the **easiest** ways to get bounding box coordinates for any location without needing GIS software or technical knowledge.

## Table of Contents
1. [Method 1: BoundingBox.klokantech.com (Easiest!)](#method-1-boundingboxklokantechcom-easiest)
2. [Method 2: geojson.io (Most Visual)](#method-2-geojsonio-most-visual)
3. [Method 3: OpenStreetMap (Most Accurate)](#method-3-openstreetmap-most-accurate)
4. [Method 4: Google Earth (For Large Areas)](#method-4-google-earth-for-large-areas)
5. [Quick Reference: Common Locations](#quick-reference-common-locations)

---

## Method 1: BoundingBox.klokantech.com (Easiest!)

**Best for:** Quick bounding boxes, city/state boundaries, named locations

**Time:** 30 seconds

### Step-by-Step

**1. Go to the website:**
```
https://boundingbox.klokantech.com/
```

**2. Search for your location:**
- Type in the search box: `Austin, Texas`
- Or: `Texas, USA`
- Or: `Downtown Austin`
- Press Enter

**3. The map will zoom to your location with a red bounding box**

**4. Copy the coordinates:**
- Look at the bottom of the page
- Find the dropdown that says "CSV"
- Click it and select **"CSV"** format
- You'll see coordinates like: `-97.9383,30.0986,-97.5698,30.5168`

**5. That's it! Use those coordinates:**
```bash
docker-compose run --rm worker add-aoi \
  --name "Austin-TX" \
  --bbox "-97.9383,30.0986,-97.5698,30.5168"
```

### Visual Example

```
┌─────────────────────────────────────────────────────────┐
│  🔍 Search: Austin, Texas               [CSV ▼]        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│         ┌─────────────────────────┐                    │
│         │                         │                    │
│         │      AUSTIN, TX         │                    │
│         │                         │                    │
│         │     (Red Box Shows)     │                    │
│         │     (Your Area)         │                    │
│         │                         │                    │
│         └─────────────────────────┘                    │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ Coordinates: -97.9383,30.0986,-97.5698,30.5168         │
└─────────────────────────────────────────────────────────┘
```

### Tips

✅ **Adjust the box:**
- Drag the **corners** of the red box to resize
- Drag the **center** to move the box
- Coordinates update automatically

✅ **Change the format:**
- Select "CSV" for our system (minx,miny,maxx,maxy)
- Ignore other formats (GeoJSON, WKT, etc.)

✅ **Zoom in/out:**
- Mouse wheel to zoom
- Double-click to zoom in
- Shift+drag to draw custom box

---

## Method 2: geojson.io (Most Visual)

**Best for:** Custom shapes, neighborhoods, irregular areas, seeing the exact boundary

**Time:** 2-3 minutes

### Step-by-Step

**1. Go to the website:**
```
https://geojson.io/
```

**2. Search for your location:**
- Use the search box in the top-left
- Type: `Austin, Texas`
- Map zooms to location

**3. Draw your area:**

**Option A: Rectangle Tool**
- Click the **rectangle icon** in the toolbar (right side)
- Click and drag to draw a rectangle
- Adjust corners as needed

**Option B: Polygon Tool**
- Click the **polygon icon** in the toolbar
- Click points around your desired area
- Double-click to close the shape

**4. Get the coordinates:**
- Look at the **right panel** (GeoJSON code)
- Find the `"coordinates"` section
- You'll see something like:
  ```json
  "coordinates": [
    [
      [-97.9383, 30.0986],
      [-97.5698, 30.0986],
      [-97.5698, 30.5168],
      [-97.9383, 30.5168],
      [-97.9383, 30.0986]
    ]
  ]
  ```

**5. Extract the bounding box:**
- Look at the coordinates
- Find: **west** (smallest longitude), **south** (smallest latitude)
- Find: **east** (largest longitude), **north** (largest latitude)

**Example:**
```
From: [[-97.9383, 30.0986], [-97.5698, 30.5168]]

west = -97.9383 (smallest X)
south = 30.0986 (smallest Y)
east = -97.5698 (largest X)
north = 30.5168 (largest Y)

Result: -97.9383,30.0986,-97.5698,30.5168
```

**6. Or save as GeoJSON and import:**
- Click **Save** → **GeoJSON**
- Save file as `austin.geojson`
- Import using the GeoJSON method (see AOI_SETUP_GUIDE.md)

### Visual Example

```
┌──────────────────────────────────────────────────────────┐
│  🔍 Austin, Texas              📐 Tools: □ ⬡ 📍          │
├──────────────────────────────────────┬───────────────────┤
│                                      │ {                 │
│    ┌─────────────────┐              │   "type": "...",  │
│    │                 │              │   "coordinates": [│
│    │   You Draw      │              │     [             │
│    │   Your Area     │              │       [-97.93,    │
│    │   Here!         │              │        30.09],    │
│    │                 │              │       [-97.56,    │
│    └─────────────────┘              │        30.51]     │
│                                      │     ]             │
│         Austin, TX                   │   ]               │
│                                      │ }                 │
└──────────────────────────────────────┴───────────────────┘
         Draw on map                    Copy coordinates
```

### Tips

✅ **Very precise:**
- Draw exactly the area you want
- Good for custom neighborhoods
- Can exclude water bodies, parks, etc.

✅ **Save the GeoJSON:**
- Better for complex shapes
- Can reuse/share with others
- Preserves exact boundaries

---

## Method 3: OpenStreetMap (Most Accurate)

**Best for:** Official city/county boundaries, precise administrative areas

**Time:** 2 minutes

### Step-by-Step

**1. Go to OpenStreetMap:**
```
https://www.openstreetmap.org/
```

**2. Search for your location:**
- Click the search box (top-left)
- Type: `Austin, Texas, United States`
- Press Enter
- Map zooms to location

**3. Adjust your view:**
- Zoom in/out to see your desired area
- Pan to center it

**4. Click "Export" button:**
- Top of page, click **"Export"**
- You'll see a blue box appear
- Adjust the box to cover your area

**5. Copy the coordinates:**
- Look at the left panel
- You'll see a box with coordinates like:
  ```
  -97.9383,30.0986,-97.5698,30.5168
  ```
- Copy these coordinates

**6. Use in command:**
```bash
docker-compose run --rm worker add-aoi \
  --name "Austin-TX" \
  --bbox "-97.9383,30.0986,-97.5698,30.5168"
```

### Advanced: Using Nominatim for Exact Boundaries

For **official city boundaries** (not just a bounding box):

**1. Go to Nominatim:**
```
https://nominatim.openstreetmap.org/
```

**2. Search:**
- Enter: `Austin, Texas`
- Click **Search**

**3. Find the result:**
- Look for "Austin, Travis County, Texas"
- Click **details**

**4. Download GeoJSON:**
- Scroll down to "Geometry"
- Click **GeoJSON** link
- Save the file
- Import using GeoJSON method

### Tips

✅ **Most accurate:**
- Uses official administrative boundaries
- Better for cities, counties, states
- Data from contributors worldwide

✅ **Good for official boundaries:**
- Not just rectangles
- Actual city limits
- Excludes water bodies automatically

---

## Method 4: Google Earth (For Large Areas)

**Best for:** States, countries, large regions, visual verification

**Time:** 3-5 minutes

### Step-by-Step

**1. Download Google Earth Pro (Free):**
```
https://www.google.com/earth/versions/#earth-pro
```

**2. Open and search:**
- Launch Google Earth
- Type location in search: `Austin, Texas`
- Press Enter

**3. Add a placemark:**
- Click **Add** → **Placemark**
- Move to corner of your area
- Click to place
- Note the coordinates shown (e.g., `30.5168, -97.9383`)

**4. Repeat for all 4 corners:**
- Northwest corner: `30.5168, -97.9383` (north, west)
- Northeast corner: `30.5168, -97.5698` (north, east)
- Southwest corner: `30.0986, -97.9383` (south, west)
- Southeast corner: `30.0986, -97.5698` (south, east)

**5. Extract min/max:**
```
west = -97.9383 (smallest longitude)
south = 30.0986 (smallest latitude)
east = -97.5698 (largest longitude)
north = 30.5168 (largest latitude)

Result: -97.9383,30.0986,-97.5698,30.5168
```

### Alternative: Use Ruler Tool

**1. Click ruler icon** (top toolbar)

**2. Measure your area:**
- Click points around boundary
- Google Earth shows area and perimeter

**3. Note corner coordinates** from status bar

### Tips

✅ **Great for visual verification:**
- See terrain, roads, buildings
- Understand the actual area
- Good for large regions

✅ **Historical imagery:**
- Check different time periods
- Verify urban vs. rural areas
- Estimate listing density

---

## Quick Reference: Common Locations

Copy-paste ready coordinates for major locations:

### Texas Cities

```bash
# Austin
--bbox "-97.9383,30.0986,-97.5698,30.5168"

# Houston
--bbox "-95.8236,29.5231,-95.0139,30.1101"

# Dallas
--bbox "-97.0392,32.6178,-96.4637,33.0238"

# San Antonio
--bbox "-98.7000,29.2136,-98.2950,29.6474"

# Fort Worth
--bbox "-97.5201,32.5553,-97.0881,32.9546"

# El Paso
--bbox "-106.6497,31.6948,-106.2425,31.9473"
```

### Major US Cities

```bash
# New York City
--bbox "-74.2591,40.4774,-73.7004,40.9176"

# Los Angeles
--bbox "-118.6682,33.7037,-118.1553,34.3373"

# San Francisco
--bbox "-122.5155,37.7034,-122.3549,37.8324"

# Chicago
--bbox "-87.9401,41.6445,-87.5241,42.0230"

# Seattle
--bbox "-122.4598,47.4810,-122.2244,47.7341"

# Boston
--bbox "-71.1912,42.2279,-70.9231,42.3969"

# Miami
--bbox "-80.3203,25.7090,-80.1300,25.8557"

# Denver
--bbox "-105.1099,39.6143,-104.5992,39.9142"

# Atlanta
--bbox "-84.5519,33.6476,-84.2897,33.8868"

# Phoenix
--bbox "-112.3231,33.2943,-111.9269,33.7457"
```

### States

```bash
# Texas
--bbox "-106.6458,25.8371,-93.5083,36.5007"

# California
--bbox "-124.4820,32.5288,-114.1312,42.0095"

# Florida
--bbox "-87.6349,24.3963,-79.9743,31.0009"

# New York State
--bbox "-79.7625,40.4772,-71.8562,45.0153"
```

### International Cities

```bash
# London, UK
--bbox "-0.5103,51.2868,0.3340,51.6919"

# Paris, France
--bbox "2.2241,48.8156,2.4699,48.9022"

# Tokyo, Japan
--bbox "139.5688,35.5304,139.9195,35.8174"

# Sydney, Australia
--bbox "150.5209,-34.1183,151.3430,-33.5781"

# Toronto, Canada
--bbox "-79.6392,43.5810,-79.1168,43.8554"
```

---

## Understanding Bounding Box Format

### What do the numbers mean?

```
-97.9383,30.0986,-97.5698,30.5168
   │       │       │       │
   │       │       │       └─ North (latitude)
   │       │       └───────── East (longitude)
   │       └───────────────── South (latitude)
   └───────────────────────── West (longitude)
```

### Visual Representation

```
        North (max latitude)
             30.5168
                │
    West ───────┼─────── East
  (min lng)     │      (max lng)
  -97.9383      │      -97.5698
                │
        South (min latitude)
             30.0986

Format: west,south,east,north
        minx,miny,maxx,maxy
```

### Rules

✅ **West < East** (longitude increases going east)
- West: -97.9383
- East: -97.5698
- ✓ Valid: -97.9383 < -97.5698

✅ **South < North** (latitude increases going north)
- South: 30.0986
- North: 30.5168
- ✓ Valid: 30.0986 < 30.5168

❌ **Common mistakes:**
- Swapping longitude and latitude
- Using (lat,lng) instead of (lng,lat)
- Getting min/max backwards

---

## Verification Tool

Want to verify your coordinates before adding? Use this online tool:

### BBox Finder
```
http://bboxfinder.com/
```

**How to use:**
1. Paste your coordinates: `-97.9383,30.0986,-97.5698,30.5168`
2. Click **Map**
3. See the box drawn on the map
4. Verify it covers your intended area

---

## Pro Tips

### 1. Start Larger, Then Refine

```bash
# First: Get rough coordinates from BoundingBox.klokantech.com
# Takes 30 seconds

# Then: Verify in BBox Finder
# Takes 30 seconds

# Finally: Adjust if needed in geojson.io
# Takes 2 minutes
```

### 2. Use Multiple Tools

- **Quick lookup:** BoundingBox.klokantech.com
- **Verification:** BBox Finder
- **Custom shapes:** geojson.io
- **Official boundaries:** Nominatim

### 3. Save Your Coordinates

Create a file to track your AOIs:

```bash
# my-aois.txt
Austin-TX: -97.9383,30.0986,-97.5698,30.5168
Houston-TX: -95.8236,29.5231,-95.0139,30.1101
Dallas-TX: -97.0392,32.6178,-96.4637,33.0238
```

### 4. Use Google for Quick Lookups

Search Google for:
```
"Austin Texas bounding box"
"Austin coordinates bbox"
```

Often finds coordinates in blog posts, documentation, etc.

### 5. Convert Existing Data

If you have coordinates in other formats:

**From (lat, lng, lat, lng):**
```
30.0986,-97.9383,30.5168,-97.5698

Convert to:
-97.9383,30.0986,-97.5698,30.5168
(swap and reorder)
```

**From center + radius:**
Use geojson.io to draw a circle, then get bbox.

---

## Complete Example: Finding Austin Coordinates

**Goal:** Get bounding box for Austin, Texas

**Method 1 (Fastest - 30 seconds):**

1. Go to: https://boundingbox.klokantech.com/
2. Search: `Austin, Texas`
3. Select: `CSV` format
4. Copy: `-97.9383,30.0986,-97.5698,30.5168`
5. Done! ✓

**Method 2 (Most Visual - 2 minutes):**

1. Go to: https://geojson.io/
2. Search: `Austin, Texas`
3. Click rectangle tool
4. Draw box around city
5. Read coordinates from GeoJSON panel
6. Extract: `-97.9383,30.0986,-97.5698,30.5168`
7. Done! ✓

**Method 3 (Most Accurate - 3 minutes):**

1. Go to: https://nominatim.openstreetmap.org/
2. Search: `Austin, Texas`
3. Click: Details for "Austin, Travis County, Texas"
4. Download: GeoJSON
5. Import: Using GeoJSON method
6. Done! ✓

---

## Troubleshooting

### "My coordinates don't work"

**Check:**
1. Format is `west,south,east,north`
2. West < East (e.g., -97.9 < -97.5)
3. South < North (e.g., 30.0 < 30.5)
4. Used comma separators (not spaces)
5. No extra characters (quotes, brackets)

### "Box is in the wrong place"

**Common issues:**
- **Swapped lat/lng:** Remember it's `lng,lat` not `lat,lng`
- **Swapped min/max:** West should be < East
- **Wrong hemisphere:** Check negative signs (US is negative longitude)

**Fix:** Use BBox Finder to visualize and debug

### "Can't find my location"

**Try:**
1. Add country: `"Austin, Texas, USA"` instead of just `"Austin"`
2. Use nearby major city as reference
3. Use GPS coordinates from Google Maps
4. Search for the county: `"Travis County, Texas"`

---

## Summary: Recommended Workflow

**For quick lookups:**
```
1. BoundingBox.klokantech.com (30 seconds)
2. Copy coordinates
3. Add to system
```

**For custom areas:**
```
1. geojson.io (2 minutes)
2. Draw your shape
3. Get coordinates or export GeoJSON
4. Add to system
```

**For official boundaries:**
```
1. Nominatim (3 minutes)
2. Search location
3. Download GeoJSON
4. Import to system
```

**My recommendation:** Start with **BoundingBox.klokantech.com** - it's fast, visual, and works great for 90% of use cases!

---

## Quick Command Template

Once you have coordinates:

```bash
# Replace with your values:
docker-compose run --rm worker add-aoi \
  --name "YourCity" \
  --bbox "west,south,east,north" \
  --description "Your description"

# Example:
docker-compose run --rm worker add-aoi \
  --name "Austin-TX" \
  --bbox "-97.9383,30.0986,-97.5698,30.5168" \
  --description "Austin city limits"
```

Happy mapping! 🗺️
