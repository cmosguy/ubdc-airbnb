"""Geocoding utilities for finding bounding boxes programmatically.

This module provides functions to query free geocoding APIs (primarily Nominatim)
to automatically find bounding box coordinates for location names.
"""

import time
from typing import Optional, Tuple

import requests
from django.core.cache import cache


class GeocodingError(Exception):
    """Base exception for geocoding errors."""

    pass


class LocationNotFoundError(GeocodingError):
    """Raised when a location cannot be found."""

    pass


class GeocodingAPIError(GeocodingError):
    """Raised when the geocoding API returns an error."""

    pass


def geocode_location(
    query: str,
    provider: str = "nominatim",
    country: Optional[str] = None,
    viewbox: Optional[str] = None,
    cache_results: bool = True,
) -> Tuple[str, float, float, float, float]:
    """
    Find bounding box coordinates for a location name.

    Args:
        query: Location name (e.g., "Austin, Texas" or "London, UK")
        provider: Geocoding provider ("nominatim", "photon")
        country: Optional 2-letter country code to limit search (e.g., "us", "gb")
        viewbox: Optional bbox to prioritize results (west,south,east,north)
        cache_results: Whether to cache results (default: True, 24 hour TTL)

    Returns:
        Tuple of (display_name, west, south, east, north)

    Raises:
        LocationNotFoundError: If location cannot be found
        GeocodingAPIError: If API request fails

    Example:
        >>> name, w, s, e, n = geocode_location("Austin, Texas")
        >>> print(f"{name}: {w},{s},{e},{n}")
        Austin, Travis County, Texas, United States: -97.9383,30.0986,-97.5698,30.5168
    """
    # Check cache first
    if cache_results:
        cache_key = f"geocode:{provider}:{query}:{country}"
        cached = cache.get(cache_key)
        if cached:
            return cached

    # Route to appropriate provider
    if provider == "nominatim":
        result = _geocode_nominatim(query, country, viewbox)
    elif provider == "photon":
        result = _geocode_photon(query)
    else:
        raise ValueError(f"Unknown provider: {provider}")

    # Cache for 24 hours
    if cache_results:
        cache.set(cache_key, result, 60 * 60 * 24)

    return result


def _geocode_nominatim(
    query: str,
    country: Optional[str] = None,
    viewbox: Optional[str] = None,
) -> Tuple[str, float, float, float, float]:
    """
    Geocode using OpenStreetMap's Nominatim API.

    Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/
    - Maximum 1 request per second
    - Provide a valid User-Agent
    - No heavy usage (use for bulk lookups should cache results)

    Args:
        query: Location to search for
        country: Optional country code filter
        viewbox: Optional viewbox to prioritize results

    Returns:
        Tuple of (display_name, west, south, east, north)
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

    if viewbox:
        params["viewbox"] = viewbox
        params["bounded"] = 1

    headers = {
        "User-Agent": "UBDC-Airbnb-Research/1.0 (https://github.com/urbanbigdatacentre/ubdc-airbnb)",
    }

    try:
        # Respect rate limiting (1 req/second)
        time.sleep(1)

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        results = response.json()

        if not results:
            raise LocationNotFoundError(f"Location not found: {query}")

        result = results[0]

        # Extract bounding box
        bbox = result.get("boundingbox")
        if not bbox or len(bbox) != 4:
            raise GeocodingAPIError(f"Invalid bounding box in response for: {query}")

        # Nominatim returns: [min_lat, max_lat, min_lon, max_lon]
        # We need: [min_lon, min_lat, max_lon, max_lat]
        min_lat, max_lat, min_lon, max_lon = map(float, bbox)

        display_name = result.get("display_name", query)

        return (display_name, min_lon, min_lat, max_lon, max_lat)

    except requests.RequestException as e:
        raise GeocodingAPIError(f"API request failed: {e}")


def _geocode_photon(query: str) -> Tuple[str, float, float, float, float]:
    """
    Geocode using Photon API (alternative to Nominatim).

    Photon is based on OpenStreetMap data but provides faster responses.
    No rate limiting, but be respectful of usage.

    Args:
        query: Location to search for

    Returns:
        Tuple of (display_name, west, south, east, north)
    """
    url = "https://photon.komoot.io/api/"

    params = {
        "q": query,
        "limit": 1,
    }

    headers = {
        "User-Agent": "UBDC-Airbnb-Research/1.0",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        features = data.get("features", [])

        if not features:
            raise LocationNotFoundError(f"Location not found: {query}")

        feature = features[0]
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        # Get display name
        display_name = properties.get("name", query)
        if "state" in properties:
            display_name += f", {properties['state']}"
        if "country" in properties:
            display_name += f", {properties['country']}"

        # Extract coordinates
        coordinates = geometry.get("coordinates")
        if not coordinates or len(coordinates) != 2:
            raise GeocodingAPIError(f"Invalid coordinates in response for: {query}")

        lon, lat = coordinates

        # Photon doesn't provide bounding boxes, create a small one around the point
        # ~0.1 degree = ~11km at equator
        buffer = 0.1
        west = lon - buffer
        east = lon + buffer
        south = lat - buffer
        north = lat + buffer

        return (display_name, west, south, east, north)

    except requests.RequestException as e:
        raise GeocodingAPIError(f"API request failed: {e}")


def bbox_to_string(west: float, south: float, east: float, north: float) -> str:
    """
    Convert bbox coordinates to string format for add-aoi command.

    Args:
        west: Western longitude
        south: Southern latitude
        east: Eastern longitude
        north: Northern latitude

    Returns:
        String in format "west,south,east,north"

    Example:
        >>> bbox_to_string(-97.9383, 30.0986, -97.5698, 30.5168)
        '-97.9383,30.0986,-97.5698,30.5168'
    """
    return f"{west},{south},{east},{north}"


def geocode_and_format(query: str, **kwargs) -> Tuple[str, str]:
    """
    Geocode location and return formatted bbox string.

    Args:
        query: Location name
        **kwargs: Additional arguments for geocode_location()

    Returns:
        Tuple of (display_name, bbox_string)

    Example:
        >>> name, bbox = geocode_and_format("Austin, Texas")
        >>> print(f"{name}: {bbox}")
        Austin, Travis County, Texas: -97.9383,30.0986,-97.5698,30.5168
    """
    display_name, west, south, east, north = geocode_location(query, **kwargs)
    bbox_string = bbox_to_string(west, south, east, north)
    return (display_name, bbox_string)


# Convenience functions for common use cases


def geocode_city(city: str, state: Optional[str] = None, country: str = "us") -> Tuple[str, str]:
    """
    Geocode a US city.

    Args:
        city: City name
        state: Optional state name or abbreviation
        country: Country code (default: "us")

    Returns:
        Tuple of (display_name, bbox_string)

    Example:
        >>> name, bbox = geocode_city("Austin", "Texas")
        >>> name, bbox = geocode_city("Austin", "TX")
    """
    query = city
    if state:
        query += f", {state}"
    return geocode_and_format(query, country=country)


def geocode_state(state: str, country: str = "us") -> Tuple[str, str]:
    """
    Geocode a US state.

    Args:
        state: State name or abbreviation
        country: Country code (default: "us")

    Returns:
        Tuple of (display_name, bbox_string)

    Example:
        >>> name, bbox = geocode_state("Texas")
        >>> name, bbox = geocode_state("TX")
    """
    query = f"{state}, USA" if country == "us" else state
    return geocode_and_format(query, country=country)


def batch_geocode(
    locations: list[str],
    delay: float = 1.0,
    **kwargs,
) -> dict[str, Tuple[str, str]]:
    """
    Geocode multiple locations with rate limiting.

    Args:
        locations: List of location names
        delay: Delay between requests in seconds (default: 1.0)
        **kwargs: Additional arguments for geocode_location()

    Returns:
        Dictionary mapping location query to (display_name, bbox_string)

    Example:
        >>> cities = ["Austin, Texas", "Houston, Texas", "Dallas, Texas"]
        >>> results = batch_geocode(cities)
        >>> for city, (name, bbox) in results.items():
        ...     print(f"{city} -> {bbox}")
    """
    results = {}

    for location in locations:
        try:
            name, bbox = geocode_and_format(location, **kwargs)
            results[location] = (name, bbox)

            # Rate limiting
            if delay > 0:
                time.sleep(delay)

        except GeocodingError as e:
            print(f"Warning: Could not geocode {location}: {e}")
            results[location] = (None, None)

    return results


__all__ = [
    "geocode_location",
    "geocode_and_format",
    "geocode_city",
    "geocode_state",
    "batch_geocode",
    "bbox_to_string",
    "GeocodingError",
    "LocationNotFoundError",
    "GeocodingAPIError",
]
