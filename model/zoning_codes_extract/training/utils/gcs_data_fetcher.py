"""
GCS Data Fetcher - Downloads training data from Google Cloud Storage.

This module handles downloading zoneomics CSV files and municode ordinances
from GCS to a local temporary directory for training.
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from dotenv import load_dotenv

# Import GCPStorage from collector
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from collector.utils.gcp_storage import GCPStorage


class GCSDataFetcher:
    """
    Fetches training data from GCS to local temporary directories.

    Maps GCS paths to local paths:
    - gs://spatially-data/zoning_codes/zoneomics/ -> <temp_dir>/zoneomics/
    - gs://spatially-data/zoning_ordinance_markdown/ -> <temp_dir>/zoning_ordinance_md/
    """

    def __init__(
        self,
        gcp_project: Optional[str] = None,
        bucket_name: Optional[str] = None,
        credentials_path: Optional[str] = None,
        cache_dir: Optional[Path] = None
    ):
        """
        Initialize GCS data fetcher.

        Args:
            gcp_project: GCP project ID (defaults to GCP_PROJECT env var)
            bucket_name: GCS bucket name (defaults to GCS_DATA_BUCKET env var)
            credentials_path: Path to service account JSON (defaults to auto-discovery)
            cache_dir: Local directory to cache downloaded data (defaults to temp dir)
        """
        # Load from environment if not provided
        if gcp_project is None:
            gcp_project = os.getenv("GCP_PROJECT")
        if bucket_name is None:
            bucket_name = os.getenv("GCS_DATA_BUCKET", "spatially-data")

        if not gcp_project:
            raise ValueError("GCP_PROJECT must be set (env var or parameter)")
        if not bucket_name:
            raise ValueError("GCS_DATA_BUCKET must be set (env var or parameter)")

        # Auto-discover credentials if not provided
        if credentials_path is None:
            # Look for service account JSON in secrets folder
            secrets_dir = Path(__file__).parent.parent.parent.parent.parent / "secrets"
            potential_creds = [
                secrets_dir / "teamspatially-storage-accessor-keys.json",
                secrets_dir / "service-account.json",
                secrets_dir / "gcp-credentials.json"
            ]
            for cred_file in potential_creds:
                if cred_file.exists():
                    credentials_path = str(cred_file)
                    print(f"Using credentials: {cred_file.name}")
                    break

        # Initialize GCS client
        self.storage = GCPStorage(
            gcp_project=gcp_project,
            bucket_name=bucket_name,
            credentials_path=credentials_path
        )

        # Setup cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.use_temp_dir = False
        else:
            # Create a temporary directory that persists for the session
            self.temp_dir = tempfile.mkdtemp(prefix="spatial_ml_training_")
            self.cache_dir = Path(self.temp_dir)
            self.use_temp_dir = True

        print(f"GCS Data Fetcher initialized")
        print(f"  Project: {gcp_project}")
        print(f"  Bucket: {bucket_name}")
        print(f"  Cache dir: {self.cache_dir}")

    def fetch_zoneomics(
        self,
        gcs_prefix: str = "zoning_codes/zoneomics",
        force_download: bool = False,
        states: Optional[List[str]] = None
    ) -> Path:
        """
        Download zoneomics CSV files from GCS.

        Args:
            gcs_prefix: GCS prefix for zoneomics data
            force_download: If True, re-download even if cache exists
            states: Optional list of states to download (e.g., ['california', 'texas'])
                   If None, downloads all states

        Returns:
            Path to local zoneomics directory
        """
        local_dir = self.cache_dir / "zoneomics"

        if local_dir.exists() and not force_download:
            print(f"Using cached zoneomics data: {local_dir}")
            return local_dir

        if states:
            print(f"Downloading zoneomics for states: {', '.join(states)}")
            print(f"  From: gs://{self.storage.bucket.name}/{gcs_prefix}/")
            local_dir.mkdir(parents=True, exist_ok=True)

            # Download each state directory separately
            for state in states:
                state_lower = state.lower().replace(' ', '-')
                state_prefix = f"{gcs_prefix}/{state_lower}"
                state_local_dir = local_dir / state_lower

                print(f"  Downloading {state_lower}...")
                state_local_dir.mkdir(parents=True, exist_ok=True)

                try:
                    self.storage.download_dir(
                        source_path=state_prefix,
                        destination_path=state_local_dir
                    )
                    print(f"    ✓ {state_lower}")
                except Exception as e:
                    print(f"    ✗ {state_lower}: {e}")
        else:
            print(f"Downloading all zoneomics data from gs://{self.storage.bucket.name}/{gcs_prefix}/")
            local_dir.mkdir(parents=True, exist_ok=True)

            self.storage.download_dir(
                source_path=gcs_prefix,
                destination_path=local_dir
            )

        print(f"✓ Downloaded zoneomics to {local_dir}")
        return local_dir

    def fetch_municode_ordinances(
        self,
        gcs_prefix: str = "zoning_ordinance_markdown",
        force_download: bool = False,
        states: Optional[List[str]] = None
    ) -> Path:
        """
        Download municode ordinance markdown files from GCS.

        Args:
            gcs_prefix: GCS prefix for municode ordinances
            force_download: If True, re-download even if cache exists
            states: Optional list of states to download (e.g., ['ca', 'tx', 'california', 'texas'])
                   Accepts both state names and abbreviations
                   If None, downloads all states

        Returns:
            Path to local municode ordinances directory
        """
        local_dir = self.cache_dir / "zoning_ordinance_md"

        if local_dir.exists() and not force_download:
            print(f"Using cached municode ordinances: {local_dir}")
            return local_dir

        if states:
            # Convert state names to abbreviations (municode uses abbreviations)
            state_abbrevs = self._normalize_states_to_abbrev(states)
            print(f"Downloading municode ordinances for states: {', '.join(state_abbrevs)}")
            print(f"  From: gs://{self.storage.bucket.name}/{gcs_prefix}/")
            local_dir.mkdir(parents=True, exist_ok=True)

            # Download each state directory separately
            for state_abbrev in state_abbrevs:
                state_prefix = f"{gcs_prefix}/{state_abbrev}"
                state_local_dir = local_dir / state_abbrev

                print(f"  Downloading {state_abbrev}...")
                state_local_dir.mkdir(parents=True, exist_ok=True)

                try:
                    self.storage.download_dir(
                        source_path=state_prefix,
                        destination_path=state_local_dir
                    )
                    print(f"    ✓ {state_abbrev}")
                except Exception as e:
                    print(f"    ✗ {state_abbrev}: {e}")
        else:
            print(f"Downloading all municode ordinances from gs://{self.storage.bucket.name}/{gcs_prefix}/")
            local_dir.mkdir(parents=True, exist_ok=True)

            self.storage.download_dir(
                source_path=gcs_prefix,
                destination_path=local_dir
            )

        print(f"✓ Downloaded municode ordinances to {local_dir}")
        return local_dir

    def fetch_all(
        self,
        force_download: bool = False,
        states: Optional[List[str]] = None
    ) -> Tuple[Path, Path]:
        """
        Download both zoneomics and municode data from GCS.

        Args:
            force_download: If True, re-download even if cache exists
            states: Optional list of states to download (e.g., ['california', 'texas', 'ca', 'tx'])
                   Accepts both state names and abbreviations
                   If None, downloads all states

        Returns:
            Tuple of (zoneomics_dir, municode_dir) paths
        """
        print("=" * 60)
        print("Fetching training data from GCS")
        if states:
            print(f"States filter: {', '.join(states)}")
        else:
            print("Downloading ALL states")
        print("=" * 60)

        zoneomics_dir = self.fetch_zoneomics(force_download=force_download, states=states)
        municode_dir = self.fetch_municode_ordinances(force_download=force_download, states=states)

        print("\n" + "=" * 60)
        print("GCS data fetch complete")
        print("=" * 60)
        print(f"Zoneomics: {zoneomics_dir}")
        print(f"Municode:  {municode_dir}")
        print("=" * 60 + "\n")

        return zoneomics_dir, municode_dir

    def _normalize_states_to_abbrev(self, states: List[str]) -> List[str]:
        """
        Convert state names to abbreviations.

        Args:
            states: List of state names or abbreviations

        Returns:
            List of state abbreviations (lowercase)
        """
        # State name to abbreviation mapping
        STATE_ABBREV = {
            "alabama": "al", "alaska": "ak", "arizona": "az", "arkansas": "ar",
            "california": "ca", "colorado": "co", "connecticut": "ct", "delaware": "de",
            "florida": "fl", "georgia": "ga", "hawaii": "hi", "idaho": "id",
            "illinois": "il", "indiana": "in", "iowa": "ia", "kansas": "ks",
            "kentucky": "ky", "louisiana": "la", "maine": "me", "maryland": "md",
            "massachusetts": "ma", "michigan": "mi", "minnesota": "mn", "mississippi": "ms",
            "missouri": "mo", "montana": "mt", "nebraska": "ne", "nevada": "nv",
            "new-hampshire": "nh", "new hampshire": "nh",
            "new-jersey": "nj", "new jersey": "nj",
            "new-mexico": "nm", "new mexico": "nm",
            "new-york": "ny", "new york": "ny",
            "north-carolina": "nc", "north carolina": "nc",
            "north-dakota": "nd", "north dakota": "nd",
            "ohio": "oh", "oklahoma": "ok", "oregon": "or", "pennsylvania": "pa",
            "rhode-island": "ri", "rhode island": "ri",
            "south-carolina": "sc", "south carolina": "sc",
            "south-dakota": "sd", "south dakota": "sd",
            "tennessee": "tn", "texas": "tx", "utah": "ut", "vermont": "vt",
            "virginia": "va", "washington": "wa",
            "west-virginia": "wv", "west virginia": "wv",
            "wisconsin": "wi", "wyoming": "wy"
        }

        abbrevs = []
        for state in states:
            state_lower = state.lower().strip()
            # Check if already an abbreviation (2 letters)
            if len(state_lower) == 2 and state_lower.isalpha():
                abbrevs.append(state_lower)
            # Check if it's a state name
            elif state_lower in STATE_ABBREV:
                abbrevs.append(STATE_ABBREV[state_lower])
            else:
                # Try with spaces replaced by hyphens
                state_hyphen = state_lower.replace(' ', '-')
                if state_hyphen in STATE_ABBREV:
                    abbrevs.append(STATE_ABBREV[state_hyphen])
                else:
                    print(f"Warning: Unknown state '{state}', skipping")

        return abbrevs

    def cleanup(self):
        """Clean up temporary directory if one was created."""
        if self.use_temp_dir and hasattr(self, 'temp_dir'):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            print(f"Cleaned up temporary directory: {self.temp_dir}")


def fetch_training_data_from_gcs(
    cache_dir: Optional[Path] = None,
    force_download: bool = False,
    credentials_path: Optional[str] = None,
    states: Optional[List[str]] = None
) -> Tuple[Path, Path]:
    """
    Convenience function to fetch training data from GCS.

    Loads GCP credentials from environment variables (GCP_PROJECT, GCS_DATA_BUCKET).

    Args:
        cache_dir: Local directory to cache data (None = use artifacts/gcs_cache/)
        force_download: If True, re-download even if cache exists
        credentials_path: Path to service account JSON (None = auto-discovery)
        states: Optional list of states to download (e.g., ['california', 'texas', 'ca', 'tx'])
               Accepts both state names and abbreviations
               If None, downloads all states

    Returns:
        Tuple of (zoneomics_dir, municode_dir) paths

    Example:
        >>> from utils.gcs_data_fetcher import fetch_training_data_from_gcs
        >>> # Download all states
        >>> zoneomics_dir, municode_dir = fetch_training_data_from_gcs()
        >>>
        >>> # Download only California and Texas
        >>> zoneomics_dir, municode_dir = fetch_training_data_from_gcs(
        ...     states=['california', 'texas']
        ... )
        >>>
        >>> preparator = TrainingDataPreparator(
        ...     zoneomics_dir=str(zoneomics_dir),
        ...     municode_dir=str(municode_dir)
        ... )
    """
    # Default to artifacts/gcs_cache/ instead of temp dir to avoid accumulation
    if cache_dir is None:
        from pathlib import Path
        cache_dir = Path(__file__).parent.parent.parent / "artifacts" / "gcs_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

    fetcher = GCSDataFetcher(
        cache_dir=cache_dir,
        credentials_path=credentials_path
    )
    return fetcher.fetch_all(force_download=force_download, states=states)


if __name__ == "__main__":
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Fetch training data from GCS")
    parser.add_argument("--cache-dir", type=str, default=None,
                        help="Local directory to cache data (default: temp dir)")
    parser.add_argument("--force", action="store_true",
                        help="Force re-download even if cache exists")
    parser.add_argument("--credentials", type=str, default=None,
                        help="Path to GCP service account JSON")

    args = parser.parse_args()

    # Load environment variables
    from pathlib import Path
    env_file = Path(__file__).parent.parent.parent.parent.parent / "secrets" / "teamspatially-project.env"
    if env_file.exists():
        load_dotenv(env_file)

    # Fetch data
    zoneomics_dir, municode_dir = fetch_training_data_from_gcs(
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
        force_download=args.force,
        credentials_path=args.credentials
    )

    print("\nFetch complete! Use these paths:")
    print(f"  --zoneomics-dir {zoneomics_dir}")
    print(f"  --municode-dir {municode_dir}")
