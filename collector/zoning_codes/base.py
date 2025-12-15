from utils.db_accessor import DBAccessor
from utils.gcp_storage import GCPStorage
from template import BaseCollector
from abc import ABC, abstractmethod
import logging
import os
import sys


class ZoningCodesBaseCollector(BaseCollector, ABC):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        if not self.logger.hasHandlers():
            # Use stdout instead of stderr for Vertex AI logging
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.gcp_storage = None
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        self.gcp_project = os.environ.get("GCP_PROJECT")
        self.db_name = os.environ.get("APP_DB_NAME")
        self.db = DBAccessor(db_name=self.db_name)

        if self.bucket_name and self.gcp_project:
            try:
                self.gcp_storage = GCPStorage(
                    gcp_project=self.gcp_project, bucket_name=self.bucket_name
                )
                self.logger.info("GCS connection established")
            except Exception as e:
                self.logger.warning(
                    f"Could not connect to GCS: {e}. Will operate without GCS features."
                )
        else:
            self.logger.warning(
                "GCS credentials not found (GCS_BUCKET_NAME or GCP_PROJECT). Will operate without GCS features."
            )

    @abstractmethod
    def download_directory(self) -> str:
        """Return the download directory path for this collector."""
        pass

    @abstractmethod
    def resource_url(self) -> str:
        """Return the resource URL for this collector."""
        pass

    @abstractmethod
    def collect(self):
        """Collect zoning codes data."""
        pass

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
        Get city_id from city name, or create city if it doesn't exist.

        Uses simple slug (e.g., "boston") by default for consistency with other collectors.
        Only adds state suffix (e.g., "springfield-ma") when there's a name conflict
        with a different state.

        Args:
            city_name: Name of the city.
            state_name: Name of the state.

        Returns:
            int: The city_id from the database.
        """
        city_slug = city_name.lower().replace(" ", "-")
        state_abbrev = state_name.lower()[:2] if state_name else ""

        self.db.connect()
        with self.db.conn.cursor() as cur:
            # First, check if city with this slug exists
            cur.execute(
                "SELECT id, state FROM cities WHERE name = %s",
                (city_slug,),
            )
            result = cur.fetchone()

            if result:
                existing_id, existing_state = result
                # Same city and same state - return existing
                if existing_state == state_name:
                    return existing_id

                # Conflict: same name but different state
                # Try with state suffix (e.g., "springfield-ma")
                slug_with_state = f"{city_slug}-{state_abbrev}"
                cur.execute(
                    "SELECT id FROM cities WHERE name = %s",
                    (slug_with_state,),
                )
                result_with_state = cur.fetchone()
                if result_with_state:
                    return result_with_state[0]

                # Create new city with state suffix
                cur.execute(
                    """
                    INSERT INTO cities (name, display_name, state)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (slug_with_state, city_name, state_name),
                )
                self.db.conn.commit()
                self.logger.info(
                    f"Created city with suffix due to conflict: {slug_with_state}"
                )
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
        """
        Insert a zoning code record. Updates if zone_code already exists for city.

        Args:
            city_id: The city's database ID.
            zone_code: The zone code (e.g., "R-1", "B-2").
            zone_subtype: Optional zone subtype/name (e.g., "Single Family Residential").
            area_acres: Optional area in acres as string (will be converted to decimal).
            description: Optional full description of the zone.
        """
        # Convert area_acres to float, handling empty strings
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
