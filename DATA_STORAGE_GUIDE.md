# Data Storage Guide - Listings & Calendars

This guide explains exactly how Airbnb listing and calendar data is stored in the PostgreSQL database, including the JSON structures and how to query them.

## Table of Contents
1. [Database Schema Overview](#database-schema-overview)
2. [Listing Data Storage](#listing-data-storage)
3. [Calendar Data Storage](#calendar-data-storage)
4. [Response Types](#response-types)
5. [Querying the Data](#querying-the-data)
6. [JSON Structure Examples](#json-structure-examples)
7. [Data Relationships](#data-relationships)

---

## Database Schema Overview

The system uses **three main tables** to store Airbnb data:

```
┌──────────────────────────────────────────────────────────────┐
│                    Data Storage Design                        │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────┐      ┌──────────────────────┐
│  app_airbnblisting  │      │  app_airbnbresponse  │
│                     │      │                      │
│  listing_id (PK)    │◄────►│  id (PK)             │
│  geom_3857 (Point)  │      │  listing_id (FK)     │
│  timestamp          │      │  type (CAL/LST/etc)  │
│  calendar_updated_at│      │  status_code         │
│  listing_updated_at │      │  payload (JSONB) ◄── Full API response!
│  reviews_updated_at │      │  url                 │
│  notes (JSONB)      │      │  query_params        │
└─────────────────────┘      │  timestamp           │
                              └──────────────────────┘
                                       ▲
                              Many-to-Many relationship
```

### Key Design Principle

**Raw API responses are stored as JSON** in `app_airbnbresponse.payload`

- ✅ **Complete audit trail** - See exactly what Airbnb returned
- ✅ **Flexible analysis** - Extract any field later using JSON queries
- ✅ **Historical data** - Track how data changes over time
- ✅ **Reprocessing** - Parse data differently without re-fetching

---

## Listing Data Storage

### Table: `app_airbnblisting`

**Purpose:** Track discovered Airbnb listings and when they were last updated

**Schema:**
```sql
CREATE TABLE app_airbnblisting (
    listing_id BIGINT PRIMARY KEY,              -- Airbnb's unique ID
    geom_3857 GEOMETRY(Point, 3857),            -- Location (Web Mercator projection)
    timestamp TIMESTAMPTZ DEFAULT NOW(),        -- When first discovered

    -- Update tracking
    listing_updated_at TIMESTAMPTZ NULL,        -- Last listing details fetch
    calendar_updated_at TIMESTAMPTZ NULL,       -- Last calendar fetch
    reviews_updated_at TIMESTAMPTZ NULL,        -- Last reviews fetch
    booking_quote_updated_at TIMESTAMPTZ NULL,  -- Last quote fetch

    -- Metadata
    notes JSONB DEFAULT '{}'                    -- Custom notes/metadata
);

-- Indexes
CREATE INDEX idx_listing_calendar_updated ON app_airbnblisting(calendar_updated_at);
CREATE INDEX idx_listing_geom ON app_airbnblisting USING GIST(geom_3857);
```

**What's Stored:**

| Field | Purpose | Example |
|-------|---------|---------|
| `listing_id` | Airbnb's unique listing ID | `12345678` |
| `geom_3857` | Geographic location as a point | `POINT(-10886494 3540992)` |
| `timestamp` | When listing was first discovered | `2025-11-03 10:23:45` |
| `calendar_updated_at` | Last time calendar was fetched | `2025-11-03 02:05:23` |
| `listing_updated_at` | Last time details were fetched | `2025-10-15 05:12:00` |
| `notes` | Custom metadata | `{"aoi_id": 1, "discovered_by": "task_123"}` |

**Example Records:**

```sql
SELECT
    listing_id,
    ST_AsText(geom_3857) as location,
    calendar_updated_at,
    listing_updated_at
FROM app_airbnblisting
LIMIT 3;
```

```
 listing_id |      location                    | calendar_updated_at  | listing_updated_at
------------+----------------------------------+---------------------+--------------------
 12345678   | POINT(-10886494.23 3540992.15)  | 2025-11-03 02:05:23 | 2025-10-15 05:12:00
 23456789   | POINT(-10887123.45 3541234.67)  | 2025-11-03 02:06:15 | 2025-10-20 05:15:30
 34567890   | POINT(-10885678.90 3539876.54)  | 2025-11-03 02:07:42 | 2025-10-25 05:20:15
```

**Important Notes:**

1. **Minimal data stored here** - Most data is in `app_airbnbresponse`
2. **Listings table is a directory** - Points to where actual data lives
3. **Timestamps track freshness** - Know when to update
4. **Geographic queries** - Fast spatial lookups via PostGIS

---

## Calendar Data Storage

### Table: `app_airbnbresponse`

**Purpose:** Store raw API responses including calendar availability data

**Schema:**
```sql
CREATE TABLE app_airbnbresponse (
    id SERIAL PRIMARY KEY,                       -- Auto-increment ID
    listing_id BIGINT,                           -- Which listing (if applicable)
    type VARCHAR(3),                             -- Response type (CAL, LST, RVW, etc.)
    status_code INT,                             -- HTTP status (200, 429, etc.)

    -- The actual data!
    payload JSONB,                               -- Full API response as JSON

    -- Request metadata
    url TEXT,                                    -- API endpoint called
    query_params JSONB,                          -- Parameters sent
    request_headers JSONB,                       -- Headers sent
    seconds_to_complete INT,                     -- Response time

    -- Tracking
    timestamp TIMESTAMPTZ DEFAULT NOW(),         -- When fetched
    ubdc_task_id UUID                            -- Celery task that created this
);

-- Indexes
CREATE INDEX idx_response_listing ON app_airbnbresponse(listing_id);
CREATE INDEX idx_response_type ON app_airbnbresponse(type);
CREATE INDEX idx_response_timestamp ON app_airbnbresponse(timestamp);
CREATE INDEX idx_response_payload ON app_airbnbresponse USING GIN(payload);
```

**Response Types:**

| Code | Type | Description |
|------|------|-------------|
| `CAL` | Calendar | 12 months of availability/pricing |
| `LST` | Listing Detail | Full listing information |
| `RVW` | Reviews | Guest reviews and ratings |
| `BQT` | Booking Quote | Price quote for specific dates |
| `SRH` | Search | Search results (multiple listings) |
| `USR` | User Detail | Host/guest profile information |

**Example Record for Calendar:**

```sql
SELECT
    id,
    listing_id,
    type,
    status_code,
    jsonb_pretty(payload) as calendar_data,
    timestamp
FROM app_airbnbresponse
WHERE type = 'CAL' AND listing_id = 12345678
ORDER BY timestamp DESC
LIMIT 1;
```

---

## Calendar Data Structure

### What's in the Payload?

The `payload` JSONB field contains **12 months** of calendar data from Airbnb's API.

### Full Calendar Response Example

```json
{
  "calendar_months": [
    {
      "year": 2025,
      "month": 11,
      "days": [
        {
          "date": "2025-11-01",
          "available": true,
          "available_for_checkin": true,
          "available_for_checkout": true,
          "bookable": true,
          "min_nights": 2,
          "max_nights": 30,
          "price": {
            "local_price": 125,
            "local_price_formatted": "£125",
            "local_currency": "GBP",
            "local_adjusted_price": 125,
            "local_adjusted_price_formatted": "£125"
          }
        },
        {
          "date": "2025-11-02",
          "available": false,
          "available_for_checkin": false,
          "available_for_checkout": false,
          "bookable": false,
          "min_nights": 1,
          "max_nights": 1125,
          "price": {
            "local_price": 0,
            "local_price_formatted": "£0",
            "local_currency": "GBP"
          }
        },
        // ... 28 more days
      ]
    },
    {
      "year": 2025,
      "month": 12,
      "days": [
        // 31 days for December
      ]
    },
    // ... 10 more months (total 12 months)
  ],
  "pdp_listing_booking_details": [
    {
      "listing_id": "12345678",
      "currency": "GBP",
      "min_nights": 2,
      "max_nights": 30
    }
  ]
}
```

### Key Calendar Fields Explained

**Per Day:**

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `date` | String | Date in YYYY-MM-DD | `"2025-11-15"` |
| `available` | Boolean | Is day available? | `true` |
| `available_for_checkin` | Boolean | Can guest check in? | `true` |
| `available_for_checkout` | Boolean | Can guest check out? | `true` |
| `bookable` | Boolean | Can be booked? | `true` |
| `min_nights` | Integer | Minimum stay length | `2` |
| `max_nights` | Integer | Maximum stay length | `30` |
| `price.local_price` | Integer | Nightly rate | `125` |
| `price.local_currency` | String | Currency code | `"GBP"` |

**Calendar States:**

```
Available Day:
{
  "available": true,
  "bookable": true,
  "price": { "local_price": 125 }
}

Blocked Day (already booked):
{
  "available": false,
  "bookable": false,
  "price": { "local_price": 0 }
}

Available but not bookable (min nights):
{
  "available": true,
  "bookable": false,  // e.g., need 2 nights minimum
  "min_nights": 2
}
```

---

## Response Types

### 1. Calendar (`CAL`)

**When:** Daily at 2 AM for all listings in enabled AOIs
**Contains:** 12 months of availability and pricing

```json
{
  "calendar_months": [
    { "year": 2025, "month": 11, "days": [...] },
    // ... 11 more months
  ]
}
```

**Storage:**
- One row per fetch
- Typically fetched daily
- ~50-100 KB per listing

### 2. Listing Detail (`LST`)

**When:** Every 14 days (12th and 24th of month)
**Contains:** Full listing information

```json
{
  "pdp_listing_details": {
    "id": "12345678",
    "name": "Beautiful Downtown Apartment",
    "description": "...",
    "property_type": "Apartment",
    "room_type": "Entire home/apt",
    "bedrooms": 2,
    "bathrooms": 1,
    "beds": 2,
    "person_capacity": 4,
    "primary_host": {
      "id": "98765432",
      "first_name": "John",
      "is_superhost": true
    },
    "amenities": [
      {"id": 1, "name": "Wifi"},
      {"id": 4, "name": "Kitchen"}
    ],
    "listing_rooms": [...],
    "photos": [...]
  }
}
```

**Storage:**
- One row per fetch
- Updated every 2 weeks
- ~200-500 KB per listing

### 3. Reviews (`RVW`)

**When:** On-demand or scheduled
**Contains:** Guest reviews and ratings

```json
{
  "reviews": [
    {
      "id": "111222333",
      "created_at": "2025-10-15T10:30:00Z",
      "comments": "Great place, highly recommend!",
      "rating": 5,
      "author": {
        "id": "44455566",
        "first_name": "Sarah"
      },
      "recipient": {
        "id": "98765432",
        "first_name": "John"
      }
    }
  ],
  "metadata": {
    "reviews_count": 42
  }
}
```

**Storage:**
- One row per page (20 reviews per page)
- Fetched on-demand
- ~10-50 KB per page

### 4. Booking Quote (`BQT`)

**When:** On-demand
**Contains:** Price breakdown for specific dates

```json
{
  "pdp_listing_booking_details": {
    "listing_id": "12345678",
    "check_in": "2025-11-15",
    "check_out": "2025-11-17",
    "guests": 2,
    "price": {
      "base_price": 250,
      "cleaning_fee": 50,
      "service_fee": 45,
      "total": 345,
      "currency": "GBP"
    }
  }
}
```

---

## Querying the Data

### Python/Django Examples

#### Get Latest Calendar for a Listing

```python
from ubdc_airbnb.models import AirBnBListing, AirBnBResponse, AirBnBResponseTypes

# Get listing
listing = AirBnBListing.objects.get(listing_id=12345678)

# Get most recent calendar
calendar = AirBnBResponse.objects.filter(
    listing_id=12345678,
    _type=AirBnBResponseTypes.calendar,
    status_code=200
).order_by('-timestamp').first()

# Access the calendar data
payload = calendar.payload
calendar_months = payload['calendar_months']

# Get November 2025 data
nov_2025 = next(
    (m for m in calendar_months if m['year'] == 2025 and m['month'] == 11),
    None
)

if nov_2025:
    for day in nov_2025['days']:
        print(f"{day['date']}: Available={day['available']}, Price={day['price']['local_price']}")
```

#### Find Available Dates

```python
# Get calendar
calendar = AirBnBResponse.objects.filter(
    listing_id=12345678,
    _type=AirBnBResponseTypes.calendar
).order_by('-timestamp').first()

# Find available dates
available_dates = []
for month in calendar.payload['calendar_months']:
    for day in month['days']:
        if day['available'] and day['bookable']:
            available_dates.append({
                'date': day['date'],
                'price': day['price']['local_price'],
                'min_nights': day['min_nights']
            })

print(f"Found {len(available_dates)} available dates")
```

#### Get All Calendars for a Listing (Time Series)

```python
# Get all calendar responses for a listing
calendars = AirBnBResponse.objects.filter(
    listing_id=12345678,
    _type=AirBnBResponseTypes.calendar,
    status_code=200
).order_by('timestamp')

# Track price changes over time for a specific date
target_date = "2025-12-25"  # Christmas

prices_over_time = []
for calendar in calendars:
    for month in calendar.payload['calendar_months']:
        for day in month['days']:
            if day['date'] == target_date:
                prices_over_time.append({
                    'fetched_at': calendar.timestamp,
                    'price': day['price']['local_price'],
                    'available': day['available']
                })

# See how Christmas pricing changed
for entry in prices_over_time:
    print(f"{entry['fetched_at']}: £{entry['price']} (available: {entry['available']})")
```

#### Get Listing Details

```python
# Get latest listing details
listing_detail = AirBnBResponse.objects.filter(
    listing_id=12345678,
    _type=AirBnBResponseTypes.listingDetail,
    status_code=200
).order_by('-timestamp').first()

# Extract information
details = listing_detail.payload['pdp_listing_details']
print(f"Name: {details['name']}")
print(f"Type: {details['property_type']}")
print(f"Bedrooms: {details['bedrooms']}")
print(f"Host: {details['primary_host']['first_name']}")
print(f"Superhost: {details['primary_host']['is_superhost']}")
```

### SQL Examples

#### Get Calendar Data for Multiple Listings

```sql
-- Get latest calendar for each listing in an AOI
WITH latest_calendars AS (
    SELECT DISTINCT ON (listing_id)
        listing_id,
        payload,
        timestamp
    FROM app_airbnbresponse
    WHERE type = 'CAL'
      AND status_code = 200
      AND listing_id IN (
          SELECT listing_id
          FROM app_airbnblisting
          WHERE ST_Intersects(geom_3857, (SELECT geom_3857 FROM app_aoishape WHERE id = 1))
      )
    ORDER BY listing_id, timestamp DESC
)
SELECT
    listing_id,
    jsonb_array_length(payload->'calendar_months') as months_count,
    timestamp as last_updated
FROM latest_calendars;
```

#### Find Listings with Availability on Specific Date

```sql
-- Find listings available on Christmas 2025
SELECT DISTINCT
    r.listing_id,
    l.geom_3857,
    day->>'date' as date,
    (day->'price'->>'local_price')::int as price
FROM app_airbnbresponse r
JOIN app_airbnblisting l ON r.listing_id = l.listing_id,
LATERAL jsonb_array_elements(r.payload->'calendar_months') as month,
LATERAL jsonb_array_elements(month->'days') as day
WHERE r.type = 'CAL'
  AND r.status_code = 200
  AND day->>'date' = '2025-12-25'
  AND (day->>'available')::boolean = true
  AND (day->>'bookable')::boolean = true
ORDER BY price;
```

#### Calculate Average Pricing by Listing

```sql
-- Average nightly rate for each listing
SELECT
    r.listing_id,
    AVG((day->'price'->>'local_price')::int) as avg_price,
    COUNT(*) as days_count
FROM app_airbnbresponse r,
LATERAL jsonb_array_elements(r.payload->'calendar_months') as month,
LATERAL jsonb_array_elements(month->'days') as day
WHERE r.type = 'CAL'
  AND r.status_code = 200
  AND (day->>'available')::boolean = true
  AND r.listing_id IN (SELECT listing_id FROM app_airbnblisting LIMIT 100)
GROUP BY r.listing_id
ORDER BY avg_price DESC;
```

#### Track Price Changes Over Time

```sql
-- See how a specific listing's December prices have changed
SELECT
    r.timestamp::date as fetched_on,
    day->>'date' as calendar_date,
    (day->'price'->>'local_price')::int as price,
    (day->>'available')::boolean as available
FROM app_airbnbresponse r,
LATERAL jsonb_array_elements(r.payload->'calendar_months') as month,
LATERAL jsonb_array_elements(month->'days') as day
WHERE r.type = 'CAL'
  AND r.listing_id = 12345678
  AND month->>'month' = '12'
  AND month->>'year' = '2025'
ORDER BY r.timestamp, day->>'date';
```

---

## Data Relationships

### Many-to-Many: Listings ↔ Responses

```sql
-- Junction table
CREATE TABLE app_airbnblisting_responses (
    id SERIAL PRIMARY KEY,
    airbnblisting_id BIGINT REFERENCES app_airbnblisting(listing_id),
    airbnbresponse_id INT REFERENCES app_airbnbresponse(id)
);
```

**Why Many-to-Many?**

1. **One listing → Many responses** (calendars over time)
2. **One response → Many listings** (search results)

**Example Query:**

```python
# Get all responses for a listing
listing = AirBnBListing.objects.get(listing_id=12345678)
all_responses = listing.responses.all()

# Filter by type
calendars = listing.responses.filter(_type=AirBnBResponseTypes.calendar)
details = listing.responses.filter(_type=AirBnBResponseTypes.listingDetail)

# Get latest of each type
latest_calendar = calendars.order_by('-timestamp').first()
latest_details = details.order_by('-timestamp').first()
```

---

## Storage Efficiency

### How Much Data?

**Per Listing:**

| Data Type | Frequency | Size | Annual Total |
|-----------|-----------|------|--------------|
| Calendar | Daily | 75 KB | ~27 MB |
| Listing Details | Bi-weekly | 300 KB | ~7.8 MB |
| Reviews | Monthly | 25 KB | 300 KB |
| **Total** | | | **~35 MB/year** |

**For 10,000 Listings:**
- **Daily:** ~750 MB (calendars)
- **Annual:** ~350 GB

**Storage Considerations:**

✅ **JSONB is compressed** by PostgreSQL
✅ **Old responses can be archived** to separate table
✅ **Indexes on `timestamp` allow** fast recent data queries
✅ **VACUUM regularly** to reclaim space

---

## Best Practices

### 1. Always Use Latest Response

```python
# Good - get most recent
calendar = AirBnBResponse.objects.filter(
    listing_id=listing_id,
    _type=AirBnBResponseTypes.calendar
).order_by('-timestamp').first()

# Avoid - might get old data
calendar = AirBnBResponse.objects.filter(
    listing_id=listing_id,
    _type=AirBnBResponseTypes.calendar
).first()  # No ordering!
```

### 2. Check Status Code

```python
# Good - verify success
calendar = AirBnBResponse.objects.filter(
    listing_id=listing_id,
    _type=AirBnBResponseTypes.calendar,
    status_code=200  # Only successful responses
).order_by('-timestamp').first()
```

### 3. Use JSON Queries for Performance

```python
# Good - database-level filtering
available_on_christmas = AirBnBResponse.objects.filter(
    _type=AirBnBResponseTypes.calendar,
    payload__calendar_months__0__days__0__date='2025-12-25',
    payload__calendar_months__0__days__0__available=True
)

# Avoid - fetching then filtering in Python
all_calendars = AirBnBResponse.objects.filter(_type=AirBnBResponseTypes.calendar)
for cal in all_calendars:  # Slow!
    # Filter in Python
```

### 4. Archive Old Data

```python
# Archive calendars older than 90 days
from datetime import timedelta
from django.utils import timezone

cutoff = timezone.now() - timedelta(days=90)

old_calendars = AirBnBResponse.objects.filter(
    _type=AirBnBResponseTypes.calendar,
    timestamp__lt=cutoff
)

# Move to archive table or delete
old_calendars.update(archived=True)
# or: old_calendars.delete()
```

---

## Summary

### Data Storage Model

```
Listings Table (app_airbnblisting)
  ├─ Minimal metadata (ID, location, timestamps)
  └─ Links to → Responses

Responses Table (app_airbnbresponse)
  ├─ Full API responses stored as JSONB
  ├─ Multiple response types (CAL, LST, RVW, BQT)
  └─ One row per API call
     ├─ Calendar: 12 months of availability/pricing
     ├─ Listing Detail: Property information
     ├─ Reviews: Guest feedback
     └─ Booking Quote: Price breakdowns
```

### Key Points

1. **Raw API responses** stored as JSON in `payload` field
2. **Historical tracking** - Multiple calendar snapshots over time
3. **Flexible querying** - Use JSONPath or SQL JSON functions
4. **Complete audit trail** - See exactly what Airbnb returned
5. **Many-to-Many** relationship between listings and responses

### Quick Access

```python
# Get listing
listing = AirBnBListing.objects.get(listing_id=12345678)

# Latest calendar
calendar = listing.responses.filter(
    _type=AirBnBResponseTypes.calendar
).order_by('-timestamp').first()

# Calendar data
payload = calendar.payload
months = payload['calendar_months']
```

That's how the data is stored! 🗄️
