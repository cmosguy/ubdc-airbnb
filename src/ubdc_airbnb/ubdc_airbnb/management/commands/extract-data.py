import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ubdc_airbnb.models import AirBnBResponse


class Command(BaseCommand):
    help = """
    Extract calendar or listing detail data from the database.
    Exports data as JSONL (JSON Lines) format for further analysis.
    """

    def add_arguments(self, parser):
        operation = parser.add_mutually_exclusive_group(required=True)
        operation.add_argument(
            "--calendar",
            action="store_true",
            help="Extract calendar data",
        )
        operation.add_argument(
            "--listing-detail",
            action="store_true",
            help="Extract listing detail data",
        )

        parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: /app/data/calendars.jsonl or /app/data/listing-details.jsonl)",
        )

        parser.add_argument(
            "--since",
            type=str,
            help="Export data since this date (YYYY-MM-DD format)",
        )

        parser.add_argument(
            "--listing-id",
            type=int,
            help="Export data for specific listing ID only",
        )

        parser.add_argument(
            "--geojson",
            action="store_true",
            help="Export as GeoJSON format (for listing details only)",
        )

    def handle(self, *args, **options):
        try:
            # Determine data type
            if options["calendar"]:
                data_type = "CAL"  # Calendar type
                default_output = "/app/data/calendars.jsonl"
            else:
                data_type = "LST"  # Listing detail type
                default_output = "/app/data/listing-details.jsonl"

            # Check for GeoJSON export
            export_geojson = options["geojson"]

            # Validate GeoJSON is only used with listing details
            if export_geojson and options["calendar"]:
                raise CommandError("GeoJSON export is only available for listing details, not calendars")

            # Get output path
            if export_geojson and not options["output"]:
                # Change default extension to .geojson
                default_output = "/app/data/listing-details.geojson"

            output_path = options["output"] or default_output

            # Build query
            queryset = AirBnBResponse.objects.filter(_type=data_type)

            # Apply filters
            if options["listing_id"]:
                queryset = queryset.filter(listing_id=options["listing_id"])

            if options["since"]:
                since_date = datetime.strptime(options["since"], "%Y-%m-%d")
                queryset = queryset.filter(timestamp__gte=since_date)

            # Order by timestamp
            queryset = queryset.order_by("timestamp")

            # Get count
            total_count = queryset.count()

            if total_count == 0:
                self.stdout.write(self.style.WARNING(f"No {data_type} data found in database"))
                return

            # Export data
            format_type = "GeoJSON" if export_geojson else "JSONL"
            self.stdout.write(f"Exporting {total_count} {data_type} responses as {format_type}...")

            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if export_geojson:
                # Export as GeoJSON
                self._export_geojson(queryset, output_path, total_count)
            else:
                # Write JSONL
                with open(output_path, "w") as f:
                    for response in queryset:
                        entry = {
                            "listing_id": response.listing_id,
                            "timestamp": response.timestamp.isoformat(),
                            "status_code": response.status_code,
                            "url": response.url,
                            "type": response._type,
                            "payload": response.payload,
                        }
                        f.write(json.dumps(entry) + "\n")

            self.stdout.write(self.style.SUCCESS(f"✓ Exported {total_count} {data_type} responses"))
            self.stdout.write(self.style.SUCCESS(f"✓ Output: {output_path}"))

            # Show host path if using /app/data
            if output_path.startswith("/app/data/"):
                host_path = output_path.replace("/app/data/", "./docker/data/")
                self.stdout.write(f"  Available on host: {host_path}")

        except Exception as e:
            raise CommandError(f"An error occurred: {str(e)}")

    def _export_geojson(self, queryset, output_path, total_count):
        """Export listing details as GeoJSON with all property attributes."""
        features = []
        skipped = 0

        for response in queryset:
            try:
                payload = response.payload

                # Extract listing detail from payload
                if not payload or "pdp_listing_detail" not in payload:
                    skipped += 1
                    continue

                listing = payload["pdp_listing_detail"]

                # Extract coordinates
                lat = listing.get("lat")
                lng = listing.get("lng")

                if lat is None or lng is None:
                    skipped += 1
                    continue

                # Build comprehensive properties object
                properties = {
                    "listing_id": response.listing_id,
                    "timestamp": response.timestamp.isoformat(),
                    "name": listing.get("name"),
                    "city": listing.get("city"),
                    "state": listing.get("state"),
                    "country": listing.get("country"),
                    "room_type": listing.get("room_type"),
                    "room_type_category": listing.get("room_type_category"),
                    "person_capacity": listing.get("person_capacity"),
                    "bedrooms": listing.get("bedrooms"),
                    "beds": listing.get("beds"),
                    "bathrooms": listing.get("bathrooms"),
                    "bathroom_label": listing.get("bathroom_label"),
                    "listing_tags": listing.get("listing_tags", []),
                    "url": response.url,
                }

                # Add host information
                host_info = listing.get("primary_host", {})
                if host_info:
                    properties["host_name"] = host_info.get("host_name")
                    properties["host_id"] = host_info.get("id")
                    properties["is_superhost"] = host_info.get("is_superhost")

                # Add pricing information
                if "pricing_quote" in listing:
                    pricing = listing["pricing_quote"]
                    properties["price_amount"] = pricing.get("rate", {}).get("amount")
                    properties["price_currency"] = pricing.get("rate", {}).get("currency")
                    properties["price_formatted"] = pricing.get("rate", {}).get("amount_formatted")

                # Add photos information
                photos = listing.get("photos", [])
                properties["photo_count"] = len(photos)
                if photos:
                    properties["primary_photo_url"] = photos[0].get("picture")

                # Add amenities information
                amenities = listing.get("listing_amenities", [])
                properties["amenity_count"] = len(amenities)
                if amenities:
                    # Extract just the amenity names
                    properties["amenities"] = [a.get("name") for a in amenities if a.get("name")]

                # Add review information
                reviews = listing.get("reviews_module", {})
                if reviews:
                    properties["review_count"] = reviews.get("total_count")
                    properties["rating"] = reviews.get("overall_rating")
                    properties["accuracy_rating"] = reviews.get("accuracy_rating")
                    properties["checkin_rating"] = reviews.get("checkin_rating")
                    properties["cleanliness_rating"] = reviews.get("cleanliness_rating")
                    properties["communication_rating"] = reviews.get("communication_rating")
                    properties["location_rating"] = reviews.get("location_rating")
                    properties["value_rating"] = reviews.get("value_rating")

                # Add availability information
                if "availability_calendar" in listing:
                    properties["has_availability_calendar"] = True

                # Create GeoJSON feature
                feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [float(lng), float(lat)]
                    },
                    "properties": properties
                }

                features.append(feature)

            except Exception as e:
                self.stderr.write(f"Warning: Skipped listing {response.listing_id}: {str(e)}")
                skipped += 1
                continue

        # Create GeoJSON FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        # Write to file
        with open(output_path, "w") as f:
            json.dump(geojson, f, indent=2)

        if skipped > 0:
            self.stdout.write(
                self.style.WARNING(f"  Skipped {skipped} listings (missing coordinates or data)")
            )
