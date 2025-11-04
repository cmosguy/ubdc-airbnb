"""Management command to add AOI by location name using geocoding."""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ubdc_airbnb.models import AOIShape
from ubdc_airbnb.utils.geocoding import (
    GeocodingError,
    LocationNotFoundError,
    geocode_and_format,
)
from ubdc_airbnb.utils.spatial import get_geom_from_bbox
from mercantile import LngLatBbox


class Command(BaseCommand):
    help = """
    Add an Area-Of-Interest by location name using geocoding.

    This command automatically finds bounding box coordinates for a location
    by querying the Nominatim API (OpenStreetMap).

    Examples:
        add-aoi-by-name "Austin, Texas"
        add-aoi-by-name "London, UK"
        add-aoi-by-name "Paris, France" --name "Paris-City"
        add-aoi-by-name "Texas" --country us
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "location",
            type=str,
            help='Location to search for (e.g., "Austin, Texas" or "London, UK")',
        )
        parser.add_argument(
            "--name",
            type=str,
            help="Custom name for the AOI (default: uses geocoded name)",
        )
        parser.add_argument(
            "--country",
            type=str,
            help="2-letter country code to limit search (e.g., us, gb, fr)",
        )
        parser.add_argument(
            "--provider",
            type=str,
            default="nominatim",
            choices=["nominatim", "photon"],
            help="Geocoding provider to use (default: nominatim)",
        )
        parser.add_argument(
            "--no-cache",
            action="store_true",
            help="Don't use cached geocoding results",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating it",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompts for large areas",
        )

    def handle(self, *args, **options):
        location = options["location"]
        custom_name = options["name"]
        country = options["country"]
        provider = options["provider"]
        use_cache = not options["no_cache"]
        dry_run = options["dry_run"]
        skip_confirm = options["yes"]

        self.stdout.write(f"🔍 Searching for: {location}")

        # Geocode the location
        try:
            display_name, bbox_string = geocode_and_format(
                location,
                provider=provider,
                country=country,
                cache_results=use_cache,
            )
        except LocationNotFoundError as e:
            raise CommandError(f"❌ {e}")
        except GeocodingError as e:
            raise CommandError(f"❌ Geocoding failed: {e}")

        self.stdout.write(self.style.SUCCESS(f"✓ Found: {display_name}"))
        self.stdout.write(f"  Bounding box: {bbox_string}")

        # Parse bbox
        try:
            west, south, east, north = map(float, bbox_string.split(","))
        except ValueError:
            raise CommandError("Invalid bounding box format received from API")

        # Validate bbox
        if west >= east:
            raise CommandError(f"Invalid bbox: west ({west}) must be < east ({east})")
        if south >= north:
            raise CommandError(f"Invalid bbox: south ({south}) must be < north ({north})")

        # Create geometry
        bbox = LngLatBbox(west, south, east, north)
        geom = get_geom_from_bbox(bbox)
        geom_3857 = geom.transform(3857, clone=True)

        # Determine AOI name
        if custom_name:
            aoi_name = custom_name
        else:
            # Use geocoded name, clean it up
            aoi_name = display_name.split(",")[0].strip()
            # Replace spaces with hyphens for consistency
            aoi_name = aoi_name.replace(" ", "-")

        # Calculate area
        area_sq_deg = (east - west) * (north - south)
        # Rough conversion to sq km (varies by latitude)
        area_sq_km = area_sq_deg * 111 * 111 * abs((north + south) / 2)

        self.stdout.write(f"\n📊 AOI Details:")
        self.stdout.write(f"  Name: {aoi_name}")
        self.stdout.write(f"  Location: {display_name}")
        self.stdout.write(f"  Bbox: {bbox_string}")
        self.stdout.write(f"  Area: ~{area_sq_km:,.0f} sq km")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN - No changes made"))
            self.stdout.write("\nTo create this AOI, run without --dry-run")
            return

        # Confirm for large areas
        if area_sq_km > 50000 and not skip_confirm:  # Larger than Scotland (~78K sq km)
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  WARNING: This is a LARGE area ({area_sq_km:,.0f} sq km)"
                )
            )
            self.stdout.write("   Data collection will take significant time and resources.")
            confirm = input("   Continue? [y/N]: ")
            if confirm.lower() not in ["y", "yes"]:
                self.stdout.write(self.style.WARNING("Cancelled"))
                return

        # Create the AOI
        try:
            with transaction.atomic():
                notes = {
                    "geocoded_from": location,
                    "display_name": display_name,
                    "bbox": bbox_string,
                    "provider": provider,
                }

                aoi = AOIShape.objects.create(
                    name=aoi_name,
                    geom_3857=geom_3857,
                    notes=notes,
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully created AOI "{aoi.name}" (ID: {aoi.pk})'
                    )
                )

                # Create grids
                self.stdout.write("🔨 Creating grids...")
                new_grids = aoi.create_grid()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Created {new_grids} grids for AOI "{aoi.name}"'
                    )
                )

                # Show next steps
                self.stdout.write(self.style.SUCCESS("\n✨ Next steps:"))
                self.stdout.write(
                    f"   1. Enable collection: edit-aoi {aoi.pk} --calendars --listing-details"
                )
                self.stdout.write(f"   2. Discover listings: find-listings {aoi.pk}")
                self.stdout.write(f"   3. View status: list-aoi")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Failed to create AOI: {str(e)}"))
            raise
