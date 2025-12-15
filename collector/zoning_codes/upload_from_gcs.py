"""
Script to upload zoning codes from GCS to the database.

This script downloads CSV files from GCS (zoning_codes/zoneomics/{state}/*.csv)
and uploads them to the zoning_codes database table.

By default, cities are skipped if the zone count in the database matches the CSV.
This makes re-runs much faster.

Usage:
    # Upload all states from GCS (skips cities with matching counts)
    python zoning_codes/upload_from_gcs.py

    # Upload a specific state
    python zoning_codes/upload_from_gcs.py --state massachusetts

    # Test mode (only process first 3 cities)
    python zoning_codes/upload_from_gcs.py --state alabama --test-mode

    # Force upload even if counts match
    python zoning_codes/upload_from_gcs.py --state massachusetts --force
"""

import argparse
import os
import sys
import logging
import pandas as pd
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.gcp_storage import GCPStorage
from utils.db_accessor import DBAccessor


class ZoningCodesGCSUploader:
    """Upload zoning codes from GCS to the database."""

    GCS_PREFIX = "zoning_codes/zoneomics"

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.gcp_project = os.environ.get("GCP_PROJECT")
        self.db_name = os.environ.get("APP_DB_NAME")

        if not self.bucket_name or not self.gcp_project:
            raise ValueError("GCS_BUCKET_NAME and GCP_PROJECT environment variables are required")

        if not self.db_name:
            raise ValueError("APP_DB_NAME environment variable is required")

        self.gcp_storage = GCPStorage(gcp_project=self.gcp_project, bucket_name=self.bucket_name)
        self.db = DBAccessor(db_name=self.db_name)
        self.logger.info(f"Connected to GCS bucket: {self.bucket_name}")
        self.logger.info(f"Database: {self.db_name}")

    def _create_zoning_codes_table(self):
        """Create the zoning_codes table in the database."""
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS zoning_codes (
                id SERIAL PRIMARY KEY,
                city_id INTEGER NOT NULL REFERENCES cities(id) ON DELETE CASCADE,
                zone_code VARCHAR(255) NOT NULL,
                zone_subtype VARCHAR(255),
                area_acres DECIMAL(12, 2),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(city_id, zone_code)
            );

            CREATE INDEX IF NOT EXISTS idx_zoning_codes_city ON zoning_codes(city_id);
            CREATE INDEX IF NOT EXISTS idx_zoning_codes_zone_code ON zoning_codes(zone_code);
        """
        )
        self.logger.info("zoning_codes table created/verified")

    def _get_or_create_city_id(self, city_name: str, state_name: str) -> int:
        """
        Get city_id from city name and state, or create city if it doesn't exist.

        Since cities.name has a UNIQUE constraint, we check by name first.

        Lookup priority:
        1. State-suffixed slug exists (e.g., "berlin-ma") - return it
        2. Simple slug with matching state - return it
        3. Simple slug exists for different state - create with state suffix
        4. No existing city - create with simple slug

        Raises:
            ValueError: If multiple cities match the query (data integrity issue)
        """
        city_slug = city_name.lower().replace(" ", "-")
        state_abbrev = state_name.lower()[:2] if state_name else ""
        slug_with_state = f"{city_slug}-{state_abbrev}"

        self.db.connect()
        with self.db.conn.cursor() as cur:
            # Priority 1: Check if state-suffixed slug already exists
            # (name is UNIQUE, so no need to filter by state)
            cur.execute(
                "SELECT id FROM cities WHERE name = %s",
                (slug_with_state,),
            )
            result = cur.fetchone()
            if result:
                return result[0]

            # Priority 2: Check for simple slug with matching state
            cur.execute(
                "SELECT id FROM cities WHERE name = %s AND state = %s",
                (city_slug, state_name),
            )
            result = cur.fetchone()
            if result:
                return result[0]

            # Priority 3: Check if simple slug exists for a different state
            cur.execute(
                "SELECT id, state FROM cities WHERE name = %s",
                (city_slug,),
            )
            result = cur.fetchone()

            if result:
                # Simple slug exists but for different state - create with state suffix
                cur.execute(
                    """
                    INSERT INTO cities (name, display_name, state)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (slug_with_state, city_name, state_name),
                )
                self.db.conn.commit()
                self.logger.info(f"Created city with state suffix due to conflict: {slug_with_state}")
                return cur.fetchone()[0]

            # No existing city - create with simple slug
            cur.execute(
                """
                INSERT INTO cities (name, display_name, state)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (city_slug, city_name, state_name),
            )
            self.db.conn.commit()
            return cur.fetchone()[0]

    def _insert_zoning_code(
        self,
        city_id: int,
        zone_code: str,
        zone_subtype: str = None,
        area_acres: str = None,
        description: str = None,
    ):
        """Insert a zoning code record. Updates if zone_code already exists for city."""
        area_value = None
        if area_acres:
            try:
                area_value = float(area_acres)
            except ValueError:
                area_value = None

        query = """
            INSERT INTO zoning_codes (city_id, zone_code, zone_subtype, area_acres, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (city_id, zone_code)
            DO UPDATE SET
                zone_subtype = EXCLUDED.zone_subtype,
                area_acres = EXCLUDED.area_acres,
                description = EXCLUDED.description,
                created_at = CURRENT_TIMESTAMP;
        """
        self.db.execute(
            query,
            (city_id, zone_code, zone_subtype or None, area_value, description or None),
        )

    def _get_zoning_code_count_for_city(self, city_id: int) -> int:
        """Get the count of zoning codes for a city in the database."""
        self.db.connect()
        with self.db.conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM zoning_codes WHERE city_id = %s",
                (city_id,),
            )
            result = cur.fetchone()
            return result[0] if result else 0

    def list_states_in_gcs(self) -> list[str]:
        """List all state directories in GCS."""
        dirs = self.gcp_storage.list_dirs(prefix=f"{self.GCS_PREFIX}/")
        # Extract state slugs from directory paths like "zoning_codes/zoneomics/california/"
        states = []
        for d in dirs:
            parts = d.rstrip("/").split("/")
            if len(parts) >= 3:
                states.append(parts[-1])
        return sorted(states)

    def list_city_files_for_state(self, state_slug: str) -> list[str]:
        """List all CSV files for a given state in GCS."""
        prefix = f"{self.GCS_PREFIX}/{state_slug}/"
        files = self.gcp_storage.list_files(prefix=prefix, recursive=True)
        return [f for f in files if f.endswith(".csv")]

    def upload_from_gcs(self, state_slug: str = None, test_mode: bool = False, force: bool = False):
        """
        Download CSVs from GCS and upload to database.

        Args:
            state_slug: If provided, only process this state. Otherwise process all states.
            test_mode: If True, only process first 3 cities per state.
            force: If True, upload even if counts match. If False, skip cities with matching counts.
        """
        self._create_zoning_codes_table()

        # Get states to process
        if state_slug:
            states = [state_slug]
        else:
            states = self.list_states_in_gcs()

        self.logger.info(f"Found {len(states)} states to process")

        total_uploaded = 0
        total_skipped = 0
        total_errors = 0

        # Create temp directory for downloads
        tmp_dir = Path("/tmp/zoning_codes_upload")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        for state_idx, state in enumerate(states):
            self.logger.info(f"Processing state {state_idx + 1}/{len(states)}: {state}")

            try:
                csv_files = self.list_city_files_for_state(state)
                self.logger.info(f"Found {len(csv_files)} CSV files for {state}")

                if test_mode:
                    csv_files = csv_files[:3]
                    self.logger.info(f"TEST MODE: Only processing first 3 cities")

                for file_idx, gcs_path in enumerate(csv_files):
                    # Extract city slug from path
                    filename = os.path.basename(gcs_path)
                    city_slug = filename.replace(".csv", "")

                    # Convert slugs to display names
                    state_name = state.replace("-", " ").title()
                    city_name = city_slug.replace("-", " ").title()

                    try:
                        # Download file to temp location
                        local_path = tmp_dir / f"{state}_{city_slug}.csv"
                        self.gcp_storage.download_file(gcs_path, str(local_path))

                        # Read CSV to get count
                        df = pd.read_csv(local_path)
                        # Count valid zone codes in CSV
                        csv_zone_count = df["zone_code"].dropna().astype(bool).sum()

                        # Get or create city in database
                        city_id = self._get_or_create_city_id(city_name, state_name)

                        # Check if we should skip this city
                        if not force:
                            db_zone_count = self._get_zoning_code_count_for_city(city_id)
                            if db_zone_count == csv_zone_count and csv_zone_count > 0:
                                self.logger.info(
                                    f"[{file_idx + 1}/{len(csv_files)}] Skipped {city_name}, {state_name}: "
                                    f"count matches ({csv_zone_count} zones)"
                                )
                                local_path.unlink()
                                total_skipped += 1
                                continue

                        # Insert zones
                        zones_inserted = 0
                        for _, row in df.iterrows():
                            zone_code = row.get("zone_code", "")
                            if pd.isna(zone_code) or not zone_code:
                                continue

                            zone_subtype = row.get("zone_subtype")
                            zone_subtype = None if pd.isna(zone_subtype) else zone_subtype

                            area_acres = row.get("area_acres")
                            area_acres = None if pd.isna(area_acres) else area_acres

                            description = row.get("description")
                            description = None if pd.isna(description) else description

                            self._insert_zoning_code(
                                city_id=city_id,
                                zone_code=str(zone_code),
                                zone_subtype=str(zone_subtype) if zone_subtype else None,
                                area_acres=str(area_acres) if area_acres else None,
                                description=str(description) if description else None,
                            )
                            zones_inserted += 1

                        # Clean up temp file
                        local_path.unlink()

                        total_uploaded += 1
                        self.logger.info(
                            f"[{file_idx + 1}/{len(csv_files)}] Uploaded {city_name}, {state_name}: {zones_inserted} zones"
                        )

                    except Exception as e:
                        self.logger.error(f"Error uploading {city_name}, {state_name}: {e}")
                        # Rollback the transaction to recover from the error
                        try:
                            self.db.conn.rollback()
                        except Exception:
                            pass
                        total_errors += 1
                        continue

            except Exception as e:
                self.logger.error(f"Error processing state {state}: {e}")
                continue

        self.logger.info(
            f"Upload complete. Uploaded: {total_uploaded}, Skipped: {total_skipped}, Errors: {total_errors}"
        )


def main():
    parser = argparse.ArgumentParser(description="Upload zoning codes from GCS to database")
    parser.add_argument(
        "--state",
        type=str,
        help="State slug to process (e.g., 'massachusetts', 'new-york'). If not provided, processes all states.",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Only process first 3 cities per state",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force upload even if zone count matches (skip optimization disabled)",
    )
    args = parser.parse_args()

    uploader = ZoningCodesGCSUploader()
    uploader.upload_from_gcs(state_slug=args.state, test_mode=args.test_mode, force=args.force)


if __name__ == "__main__":
    main()
