# Airbnb Calendar Collection System - Complete Guide

This guide explains how the UBDC Airbnb system automatically collects calendar data from Airbnb listings on a scheduled basis.

## Table of Contents
1. [System Overview](#system-overview)
2. [The Scheduling System (Celery Beat)](#the-scheduling-system-celery-beat)
3. [The Complete Data Flow](#the-complete-data-flow)
4. [Code Walkthrough](#code-walkthrough)
5. [Database Schema](#database-schema)
6. [Configuration](#configuration)

---

## System Overview

The calendar collection system is a **distributed task queue** system that:

1. **Schedules** calendar collection jobs to run automatically every day at 2 AM
2. **Distributes** thousands of collection tasks across multiple worker processes
3. **Collects** calendar availability data from Airbnb's API for each listing
4. **Stores** the raw API responses in a PostgreSQL database for analysis

### Key Components

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Celery    │      │  RabbitMQ   │      │   Celery    │      │  PostgreSQL │
│    Beat     │─────▶│   Broker    │─────▶│   Workers   │─────▶│  Database   │
│ (Scheduler) │      │   (Queue)   │      │ (Executors) │      │  (Storage)  │
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
     Timer              Message Bus         Task Execution      Data Persistence
```

---

## The Scheduling System (Celery Beat)

### What is Celery Beat?

**Celery Beat** is a scheduler that kicks off tasks at regular intervals. Think of it like a **cron job** but integrated with your task queue.

### Configuration Location

**File:** `src/ubdc_airbnb/core/celery.py`

```python
app.conf.beat_schedule = {
    "op_update_calendar_periodical": {
        "task": "ubdc_airbnb.operations.calendars.op_update_calendar_periodical",
        "schedule": crontab(minute=0, hour=2),  # Every day at 2:00 AM
        "kwargs": {"use_aoi": True},  # Only scan enabled AOIs
    },
}
```

**What this means:**
- **Task Name:** `op_update_calendar_periodical` (the scheduled job identifier)
- **Schedule:** `crontab(minute=0, hour=2)` = Every day at 2:00 AM
- **Parameters:** `use_aoi=True` = Only collect calendars for AOIs marked for collection

### Other Scheduled Tasks

The system also schedules:

```python
# Update listing details twice per month (12th and 24th at 5 AM)
"op_update_listing_details_periodical": {
    "schedule": crontab(minute=0, hour=5, day_of_month="12,24"),
}

# Discover new listings weekly (7th, 14th, 21st, 28th at 5 AM)
"op_discover_new_listings_periodical": {
    "schedule": crontab(minute=0, hour=5, day_of_month="7,14,21,28"),
}
```

---

## The Complete Data Flow

Let me walk you through the **entire journey** from schedule trigger to database storage:

### Timeline: A Day in the Life of Calendar Collection

```
02:00 AM ──────────────────────────────────────────────────────────▶ Time

    │
    ├─ [1] Celery Beat triggers scheduled task
    │      File: core/celery.py:51-55
    │
    ├─ [2] op_update_calendar_periodical() executes
    │      File: operations/calendars.py:84
    │      • Queries database for listings to update
    │      • Filters by AOI if enabled
    │      • Chunks listings into batches of 100
    │
    ├─ [3] Creates task groups for each batch
    │      File: operations/calendars.py:109-116
    │      • Batch 1: listing_ids [1, 2, 3, ..., 100]
    │      • Batch 2: listing_ids [101, 102, ..., 200]
    │      • Batch N: listing_ids [...]
    │
    ├─ [4] Publishes tasks to RabbitMQ queue
    │      Queue: "calendar" (dedicated queue)
    │      • Each task is a message in the queue
    │      • Workers subscribe to this queue
    │
    ├─ [5] Workers pick up tasks (parallel execution)
    │      File: tasks.py:98
    │      Worker 1: task_update_calendar(listing_id=1)
    │      Worker 2: task_update_calendar(listing_id=2)
    │      Worker 3: task_update_calendar(listing_id=3)
    │      ...
    │
    ├─ [6] Each worker makes API call to Airbnb
    │      File: airbnb_api.py:189
    │      GET https://www.airbnb.co.uk/api/v2/calendar_months
    │      Via Proxy: Oxylabs/Zyte
    │      Params: listing_id, year, month, count=12
    │
    ├─ [7] API response received
    │      Status: 200 OK (hopefully!)
    │      Content: JSON with 12 months of availability data
    │      Size: ~50-100 KB per listing
    │
    ├─ [8] Response saved to database
    │      File: managers.py:99-124
    │      Table: app_airbnbresponse
    │      • Full JSON payload stored
    │      • Status code, headers, timing saved
    │
    └─ [9] Listing record updated
           File: tasks.py:119-121
           Table: app_airbnblisting
           • calendar_updated_at = NOW()
           • Response linked via Many-to-Many

Complete! ✓
```

---

## Code Walkthrough

Let's dive deep into each component with detailed code explanations.

### Step 1: The Scheduler Triggers

**File:** `core/celery.py` (lines 51-55)

```python
"op_update_calendar_periodical": {
    "task": "ubdc_airbnb.operations.calendars.op_update_calendar_periodical",
    "schedule": crontab(minute=0, hour=2),  # Every day at 2:00 AM
    "kwargs": {"use_aoi": True},
},
```

**What happens:**
- At 2:00 AM server time, Celery Beat wakes up
- Checks its schedule: "Is `op_update_calendar_periodical` due?"
- Publishes a single message to RabbitMQ to execute this operation

---

### Step 2: The Operation Coordinator

**File:** `operations/calendars.py` (lines 84-133)

```python
@shared_task(acks_late=False)
def op_update_calendar_periodical(use_aoi=True, **kwargs) -> None:
    """
    Main scheduled task that runs daily at 2 AM.
    Generates calendar collection tasks for all eligible listings.
    """
    start_of_today = start_of_day()  # 00:00:00 today
    end_of_today = end_of_day()      # 23:59:59 today

    # Step 2A: Find which listings need calendar updates
    if use_aoi:
        # Only listings in AOIs marked with collect_calendars=True
        qs_listings = AirBnBListing.objects.for_purpose("calendar")
    else:
        # All listings in database
        qs_listings = AirBnBListing.objects.all()

    # Step 2B: Optional - only update "stale" calendars
    if kwargs.get("stale", False):
        # Skip listings already updated today
        q = Q(calendar_updated_at__lt=start_of_today) | Q(calendar_updated_at=None)
        qs_listings = qs_listings.filter(q)

    # Step 2C: Process in chunks (default: 100 listings per group)
    chunk_size = settings.CELERY_TASK_CHUNK_SIZE  # Usually 100
    total_listings = qs_listings.count()
    logger.info(f"Processing {total_listings} listings")

    listing_ids = qs_listings.values_list("listing_id", flat=True)
    batch = []

    for idx, listing in enumerate(listing_ids.iterator(chunk_size=chunk_size * 2)):
        batch.append(listing)

        # When batch is full, create task group
        if idx % chunk_size == 0 and idx > 0:
            process_group(batch)
            batch.clear()

    # Process remaining listings
    process_group(batch)
```

**Key Concepts:**

1. **AOI Filtering (`use_aoi=True`):**
   - AOI = Area of Interest (geographic polygons defined in QGIS)
   - Only listings within AOIs marked `collect_calendars=True` are updated
   - Saves API calls for listings you don't care about

2. **Stale Filtering:**
   - Prevents duplicate work if the job runs multiple times in a day
   - Only updates listings where `calendar_updated_at < today 00:00`

3. **Chunking:**
   - Splitting 10,000 listings into groups of 100
   - Each group becomes a separate task group in RabbitMQ
   - Enables parallel processing and progress tracking

---

### Step 3: Creating Task Groups

**File:** `operations/calendars.py` (lines 107-116)

```python
def process_group(batch: list[int]) -> None:
    """Create a group of calendar update tasks for a batch of listing IDs."""
    logger.info(f"Submitting job for {len(batch)} listings")

    # Create a group of tasks (parallel execution)
    job = group(
        task_update_calendar.s(listing_id=listing_id).set(expires=end_of_today)
        for listing_id in batch
    )

    # Execute the group asynchronously
    group_result: AsyncResult[GroupResult] = job.apply_async()
    group_result.save()

    # Track the group in database for monitoring
    group_task = UBDCGroupTask.objects.get(group_task_id=group_result.id)
    group_task.op_name = task_update_calendar.name
    group_task.op_initiator = op_update_calendar_periodical.name
    group_task.op_kwargs = {"listing_id": batch}
    group_task.save()
```

**What's a Task Group?**

A **group** is a Celery primitive that executes multiple tasks **in parallel**:

```python
# This creates 3 tasks that run simultaneously
group([
    task_update_calendar.s(listing_id=123),
    task_update_calendar.s(listing_id=456),
    task_update_calendar.s(listing_id=789),
])
```

**Why set expiration?**
```python
.set(expires=end_of_today)
```
- If a task isn't executed by end of day, it's discarded
- Prevents old tasks from running the next day
- Keeps the queue clean

---

### Step 4: The Individual Calendar Task

**File:** `tasks.py` (lines 97-123)

```python
@shared_task(bind=True, acks_late=True)
def task_update_calendar(
    self: BaseTaskWithRetry,
    listing_id: int,
    months: int = 12,
) -> int:
    """
    Fetch calendar for a single listing and store in database.

    Args:
        listing_id: Airbnb listing ID
        months: Number of months to fetch (default: 12)

    Returns:
        listing_id on success
    """

    # Step 4A: Get or create the listing record
    listing_entry, created = AirBnBListing.objects.get_or_create(listing_id=listing_id)
    logger.info(f"Listing: {listing_id} created: {created}")

    # Step 4B: Fetch calendar from Airbnb API
    ubdc_response = AirBnBResponse.objects.fetch_response(
        type=AirBnBResponseTypes.calendar,
        calendar_months=months,
        task_id=self.request.id,  # Links response to this task
        asset_id=listing_id,
    )

    # Step 4C: Link response to listing
    listing_entry.responses.add(ubdc_response)

    # Step 4D: Update timestamp
    listing_entry.calendar_updated_at = timezone.now()
    listing_entry.save()

    return listing_entry.listing_id
```

**Decorator Explanation:**

```python
@shared_task(bind=True, acks_late=True)
```

- **`bind=True`**: Gives access to `self.request.id` (task ID)
- **`acks_late=True`**: Only acknowledge task after completion
  - If worker crashes mid-task, task is re-queued
  - Ensures data isn't lost

---

### Step 5: Fetching from Airbnb API

**File:** `managers.py` (lines 33-97)

```python
def fetch_response(
    self,
    type: "app_models.AirBnBResponseTypes",
    task_id: str | None = None,
    **kwargs,
):
    """Make a request to Airbnb API and save response to database."""
    from ubdc_airbnb.airbnb_interface.airbnb_api import AirbnbApi

    # Step 5A: Create API client with proxy
    airbnb_client = AirbnbApi(proxy=settings.AIRBNB_PROXY)

    # Step 5B: Match request type to API method
    match type:
        case AirBnBResponseTypes.calendar:
            method_name = "get_calendar"
            kwargs.update(listing_id=asset_id)
        # ... other cases ...

    method = getattr(airbnb_client, method_name)

    # Step 5C: Execute the API request
    response = method(**kwargs)  # This makes the HTTP call

    # Step 5D: Save response to database
    obj = self.create_from_response(
        response=response,
        type=type,
        task_id=task_id,
        listing_id=listing_id,
    )

    return obj
```

**The Actual API Call:**

**File:** `airbnb_api.py` (lines 189-215)

```python
def get_calendar(
    self,
    listing_id,
    starting_month=None,
    starting_year=None,
    calendar_months=12,
) -> Response:
    """Get availability calendar for a given listing."""

    # Default to current month/year
    if not starting_month:
        starting_month = datetime.utcnow().month
    if not starting_year:
        starting_year = datetime.utcnow().year

    # Build query parameters
    params = {
        "year": str(starting_year),
        "listing_id": str(listing_id),
        "_format": "with_conditions",
        "count": str(calendar_months),
        "month": str(starting_month),
    }

    # Make GET request through proxy
    r = self._session.get(
        settings.AIRBNB_API_ENDPOINT + "/v2/calendar_months",
        params=params
    )

    return r
```

**Example API Request:**

```
GET https://www.airbnb.co.uk/api/v2/calendar_months?year=2025&listing_id=12345&_format=with_conditions&count=12&month=11
Proxy: http://username:password@pr.oxylabs.io:7777
Headers:
  x-airbnb-api-key: d306zoyjsyarp7ifhu67rjxn52tv0t20
  user-agent: Mozilla/5.0 ...
  accept: application/json
```

**Example API Response:**

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
          "price": {
            "local_price": 150,
            "local_currency": "GBP"
          },
          "min_nights": 2,
          "max_nights": 30
        },
        // ... 29 more days
      ]
    },
    // ... 11 more months
  ],
  "metadata": {
    "listing_id": "12345"
  }
}
```

---

### Step 6: Saving Response to Database

**File:** `managers.py` (lines 99-195)

```python
def create_from_response(
    self,
    response: "Response",
    type: str,
    task_id: str | None = None,
    listing_id: int | None = None,
):
    """Parse HTTP response and save to database."""

    status_code = response.status_code

    # Try to parse JSON
    try:
        payload = response.json()
    except JSONDecodeError as e:
        # If response is malformed, save as base64
        payload = encapsulate_payload(response)

    # Handle different status codes
    match status_code:
        case 200:
            # Success!
            pass
        case 429:
            # Rate limited - retry
            should_raise = UBDCRetriableError("429 error, retrying", response)
        case 403:
            # Forbidden - might be blocked
            pass
        case 503:
            # Service unavailable - retry
            should_raise = UBDCRetriableError("503 error, retrying", response)

    # Create database record
    params = {
        "_type": type,
        "listing_id": listing_id,
        "status_code": status_code,
        "request_headers": dict(**response.request.headers),
        "payload": payload,  # Full JSON stored here
        "url": response.url,
        "query_params": query_params_from_url(response.url),
        "seconds_to_complete": response.elapsed.seconds,
    }

    if task_id:
        # Update existing or create
        obj, _ = self.update_or_create(ubdc_task=ubdc_task, defaults={**params})
    else:
        # Create new
        obj = self.create(**params)

    return obj
```

---

## Database Schema

### Table: `app_airbnblisting`

Stores information about Airbnb listings.

```sql
CREATE TABLE app_airbnblisting (
    listing_id BIGINT PRIMARY KEY,           -- Airbnb's listing ID
    geom_3857 GEOMETRY(Point, 3857),         -- Geographic location
    timestamp TIMESTAMPTZ,                    -- When discovered
    calendar_updated_at TIMESTAMPTZ,          -- Last calendar fetch
    listing_updated_at TIMESTAMPTZ,           -- Last details fetch
    reviews_updated_at TIMESTAMPTZ,           -- Last reviews fetch
    booking_quote_updated_at TIMESTAMPTZ,     -- Last quote fetch
    notes JSONB DEFAULT '{}'                  -- Misc metadata
);
```

**Key Field:**
- `calendar_updated_at` - Tracks when calendar was last fetched
- Used to determine if calendar is "stale"

---

### Table: `app_airbnbresponse`

Stores raw API responses.

```sql
CREATE TABLE app_airbnbresponse (
    id SERIAL PRIMARY KEY,
    listing_id BIGINT,                        -- Which listing (if applicable)
    type VARCHAR(3),                          -- cal, rev, det, etc.
    status_code INT,                          -- HTTP status (200, 429, etc.)
    payload JSONB,                            -- Full API response JSON
    request_headers JSONB,                    -- Request headers sent
    url TEXT,                                 -- Full URL called
    query_params JSONB,                       -- Parsed query params
    seconds_to_complete INT,                  -- API response time
    timestamp TIMESTAMPTZ DEFAULT NOW()       -- When fetched
);

CREATE INDEX idx_response_listing ON app_airbnbresponse(listing_id);
CREATE INDEX idx_response_type ON app_airbnbresponse(type);
```

**Why store full responses?**
- **Auditability**: Can review exactly what Airbnb returned
- **Reprocessing**: Can reparse data without re-fetching
- **Analysis**: Research how Airbnb's API changes over time

---

### Table: `app_airbnblisting_responses` (Many-to-Many)

Links listings to their responses.

```sql
CREATE TABLE app_airbnblisting_responses (
    id SERIAL PRIMARY KEY,
    airbnblisting_id BIGINT REFERENCES app_airbnblisting(listing_id),
    airbnbresponse_id INT REFERENCES app_airbnbresponse(id)
);
```

**Why Many-to-Many?**
- One listing has many responses (calendars over time)
- One response can relate to many listings (search results)

---

## Configuration

### Environment Variables

```bash
# Celery task chunk size (how many listings per batch)
CELERY_TASK_CHUNK_SIZE=100

# Proxy configuration
PROXY_PROVIDER=oxylabs
OXYLABS_USERNAME=your-username
OXYLABS_PASSWORD=your-password
```

### Celery Worker Configuration

**Starting a worker:**

```bash
# Start worker listening to default queue
celery -A core worker -l info

# Start worker for calendar queue specifically
celery -A core worker -l info -Q calendar

# Start multiple workers (horizontal scaling)
celery -A core worker -l info --concurrency=10
```

**Key Settings:**

**File:** `core/celery.py`

```python
# Route calendar tasks to dedicated queue
task_routes = {
    "ubdc_airbnb.tasks.task_update_calendar": {"queue": "calendar"},
}

# Retry configuration
CELERY_TASK_ACKS_LATE = True  # Only acknowledge after completion
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Only fetch 1 task at a time
```

---

## Monitoring & Troubleshooting

### Check Task Status

```python
from ubdc_airbnb.models import UBDCGroupTask, AirBnBListing

# Find recent calendar collections
recent_calendars = AirBnBListing.objects.filter(
    calendar_updated_at__gte=timezone.now() - timedelta(days=1)
)
print(f"Updated {recent_calendars.count()} calendars in last 24 hours")

# Check task groups
groups = UBDCGroupTask.objects.filter(
    op_name="ubdc_airbnb.tasks.task_update_calendar"
).order_by('-timestamp')[:10]

for group in groups:
    print(f"Group {group.group_task_id}: {group.timestamp}")
```

### Common Issues

**1. No calendars being collected**

Check:
- Is Celery Beat running? `docker ps | grep beat`
- Are AOIs marked for collection? `collect_calendars=True`
- Check logs: `docker logs ubdc-airbnb-beat-1`

**2. Tasks stuck in queue**

Check:
- Are workers running? `celery -A core inspect active`
- Is RabbitMQ healthy? `docker logs ubdc-airbnb-rabbit-1`
- Check queue size: Visit http://localhost:15672

**3. API errors (429, 403)**

Check:
- Proxy credentials valid?
- Rate limiting kicking in? (Slow down workers)
- Test proxy: `curl -x http://user:pass@pr.oxylabs.io:7777 https://airbnb.co.uk`

---

## Performance Metrics

### Typical Numbers

With **75 active workers** and Oxylabs proxy:

- **Requests/hour:** ~17,000
- **Calendars/day:** ~400,000 (assuming 24-hour collection window)
- **API response time:** 1-3 seconds per request
- **Success rate:** >95% (with retries)

### Scaling Considerations

**To increase throughput:**

1. **Add more workers:**
   ```bash
   docker-compose up -d --scale worker=100
   ```

2. **Increase concurrency per worker:**
   ```bash
   celery -A core worker --concurrency=20
   ```

3. **Use better proxy:**
   - Residential proxies (Oxylabs) faster than datacenter
   - Multiple proxy accounts for IP rotation

4. **Optimize chunking:**
   ```bash
   # Smaller chunks = more parallelism
   CELERY_TASK_CHUNK_SIZE=50
   ```

---

## Summary

The calendar collection system is a **sophisticated distributed workflow** that:

1. **Schedules** via Celery Beat at 2 AM daily
2. **Queries** database for listings needing updates
3. **Chunks** listings into batches of 100
4. **Distributes** tasks across worker pool via RabbitMQ
5. **Fetches** calendar data through Oxylabs proxy
6. **Stores** full API responses in PostgreSQL
7. **Tracks** progress and errors for monitoring

All of this happens **automatically**, handling thousands of listings per hour, with built-in retry logic and error handling!

---

## Next Steps

To learn more about:
- **Discovery:** How listings are initially found → See `operations/discovery.py`
- **Reviews Collection:** How reviews are fetched → See `operations/reviews.py`
- **Spatial Grids:** How areas are divided for discovery → See `utils/grids.py`
- **Proxy Service:** How requests are routed → See `proxy/README.md`
