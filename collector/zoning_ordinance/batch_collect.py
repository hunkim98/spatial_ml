"""
Batch Collection Script for Municode Zoning Ordinances

This script collects zoning ordinances from all municipalities across all states
available on library.municode.com.

Features:
- Discovers all states and municipalities automatically
- Gets the correct resource URL with nodeId for each municipality
- Tracks progress in a JSON file for resuming interrupted runs
- Saves discovered URLs to a manifest file for reference

Usage:
    # Collect all states
    python batch_collect.py

    # Collect specific states only
    python batch_collect.py --states al,ma,ca

    # Discovery only (don't download, just build manifest)
    python batch_collect.py --discover-only

    # Resume from where you left off
    python batch_collect.py --resume
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils.scrapers.municode_discovery import MunicodeDiscovery
from utils.smart_arg_parser import SmartArgItem, SmartArgParser
from municode import MunicodeZoningOrdinanceCollector


class BatchCollector:
    """Batch collector for all Municode municipalities."""

    PROGRESS_FILE = "tmp/batch_progress.json"
    MANIFEST_FILE = "tmp/municode_manifest.json"

    def __init__(self, states: Optional[list[str]] = None, discover_only: bool = False, force: bool = False):
        """
        Initialize the batch collector.

        Args:
            states: Optional list of state abbreviations to collect. If None, collects all states.
            discover_only: If True, only discover URLs without downloading.
            force: If True, re-discover URLs even if they already exist (useful to fix invalid URLs).
        """
        self.states = [s.lower() for s in states] if states else None
        self.discover_only = discover_only
        self.force = force
        self.discovery = MunicodeDiscovery(headless=True)

        # Ensure tmp directory exists
        os.makedirs("tmp", exist_ok=True)

        # Load or initialize progress
        self.progress = self._load_progress()
        self.manifest = self._load_manifest()

    def _load_progress(self) -> dict:
        """Load progress from file or return empty dict."""
        if os.path.exists(self.PROGRESS_FILE):
            with open(self.PROGRESS_FILE, "r") as f:
                return json.load(f)
        return {
            "completed": [],  # List of "state/municipality" that are done
            "failed": [],  # List of "state/municipality" that failed
            "last_state": None,
            "last_municipality": None,
            "started_at": None,
            "updated_at": None,
        }

    def _save_progress(self):
        """Save progress to file."""
        self.progress["updated_at"] = datetime.now().isoformat()
        with open(self.PROGRESS_FILE, "w") as f:
            json.dump(self.progress, f, indent=2)

    def _load_manifest(self) -> dict:
        """Load manifest from file or return empty dict."""
        if os.path.exists(self.MANIFEST_FILE):
            with open(self.MANIFEST_FILE, "r") as f:
                return json.load(f)
        return {
            "states": {},  # state_abbrev -> list of municipalities
            "urls": {},  # "state/municipality" -> resource_url with nodeId
            "discovered_at": None,
        }

    def _save_manifest(self):
        """Save manifest to file."""
        self.manifest["discovered_at"] = datetime.now().isoformat()
        with open(self.MANIFEST_FILE, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def _is_completed(self, state: str, municipality: str) -> bool:
        """Check if a municipality has been completed."""
        key = f"{state}/{municipality}"
        return key in self.progress["completed"]

    def _mark_completed(self, state: str, municipality: str):
        """Mark a municipality as completed."""
        key = f"{state}/{municipality}"
        if key not in self.progress["completed"]:
            self.progress["completed"].append(key)
        self._save_progress()

    def _mark_failed(self, state: str, municipality: str, error: str):
        """Mark a municipality as failed."""
        key = f"{state}/{municipality}"
        self.progress["failed"].append({"key": key, "error": str(error), "time": datetime.now().isoformat()})
        self._save_progress()

    def discover_all(self):
        """Discover all states and municipalities, building the manifest."""
        print("=" * 60)
        print("DISCOVERING ALL STATES AND MUNICIPALITIES")
        print("=" * 60)

        all_states = self.discovery.list_states()

        # Filter states if specified
        if self.states:
            all_states = [s for s in all_states if s["abbrev"] in self.states]
            print(f"Filtering to {len(all_states)} states: {self.states}")

        for state_info in all_states:
            state_abbrev = state_info["abbrev"]
            state_name = state_info["name"]

            print(f"\n{'='*60}")
            print(f"Discovering municipalities in {state_name} ({state_abbrev.upper()})")
            print(f"{'='*60}")

            # Check if we already have this state in manifest
            if state_abbrev in self.manifest["states"]:
                municipalities = self.manifest["states"][state_abbrev]
                print(f"Already discovered {len(municipalities)} municipalities")
            else:
                try:
                    municipalities = self.discovery.list_municipalities(state_abbrev)
                    self.manifest["states"][state_abbrev] = municipalities
                    self._save_manifest()
                    print(f"Discovered {len(municipalities)} municipalities in {state_name}")
                except Exception as e:
                    print(f"Error discovering {state_name}: {e}")
                    continue

            # Get URLs for each municipality (even if state was already in manifest)
            for muni in municipalities:
                key = f"{state_abbrev}/{muni['slug']}"
                
                # Check if we need to skip or re-discover
                if key in self.manifest["urls"]:
                    existing_url = self.manifest["urls"][key]
                    # Check if existing URL has an invalid nodeId (pure numeric)
                    has_invalid_nodeid = False
                    if "nodeId=" in existing_url:
                        node_id = existing_url.split("nodeId=")[-1].split("&")[0]
                        if node_id.isdigit():
                            has_invalid_nodeid = True
                            print(f"  URL for {muni['slug']} has invalid numeric nodeId: {node_id}")
                    
                    if not self.force and not has_invalid_nodeid:
                        print(f"  Already have URL for {muni['slug']}, skipping")
                        continue
                    elif has_invalid_nodeid:
                        print(f"  Re-discovering URL for {muni['slug']} (invalid nodeId)...")
                    else:
                        print(f"  Force re-discovering URL for {muni['slug']}...")

                print(f"  Getting URL for {muni['slug']}...")
                try:
                    url = self.discovery.get_municipality_codes_url(state_abbrev, muni["slug"])
                    if url:
                        self.manifest["urls"][key] = url
                        self._save_manifest()
                        print(f"    -> {url}")
                    else:
                        print(f"    -> No URL found")
                except Exception as e:
                    print(f"    -> Error: {e}")

                # Small delay to be respectful
                time.sleep(1)

        print(f"\n{'='*60}")
        print(f"DISCOVERY COMPLETE")
        print(f"Total municipalities: {len(self.manifest['urls'])}")
        print(f"Manifest saved to: {self.MANIFEST_FILE}")
        print(f"{'='*60}")

    def collect_all(self):
        """Collect zoning ordinances for all discovered municipalities."""
        if not self.manifest["urls"]:
            print("No URLs in manifest. Run with --discover-only first or let discovery run.")
            self.discover_all()

        if self.discover_only:
            print("Discovery only mode - not downloading files")
            return

        print("\n" + "=" * 60)
        print("COLLECTING ZONING ORDINANCES")
        print("=" * 60)

        # Set start time if not set
        if not self.progress["started_at"]:
            self.progress["started_at"] = datetime.now().isoformat()
            self._save_progress()

        total = len(self.manifest["urls"])
        completed = len(self.progress["completed"])
        print(f"Total municipalities: {total}")
        print(f"Already completed: {completed}")
        print(f"Remaining: {total - completed}")

        for idx, (key, url) in enumerate(self.manifest["urls"].items(), 1):
            state_abbrev, municipality = key.split("/")

            # Skip if already completed
            if self._is_completed(state_abbrev, municipality):
                continue

            print(f"\n[{idx}/{total}] Collecting {municipality}, {state_abbrev.upper()}")
            print(f"URL: {url}")

            try:
                collector = MunicodeZoningOrdinanceCollector(
                    state_abbrev=state_abbrev,
                    municipality=municipality,
                    resource_url=url,
                )
                collector.collect()
                self._mark_completed(state_abbrev, municipality)
                print(f"Successfully collected {municipality}, {state_abbrev.upper()}")

                # Normal delay between municipalities
                time.sleep(5)

            except Exception as e:
                error_str = str(e)
                print(f"Error collecting {municipality}, {state_abbrev.upper()}: {error_str}")
                self._mark_failed(state_abbrev, municipality, error_str)

                # If downloads are being blocked, wait longer before trying next municipality
                if "blocked" in error_str.lower() or "consecutive failures" in error_str.lower():
                    print(f"\n{'='*60}")
                    print("Downloads appear to be blocked. Waiting 60 seconds before next municipality...")
                    print(f"{'='*60}")
                    time.sleep(60)
                else:
                    time.sleep(10)  # Normal error - shorter delay

            # Update progress tracking
            self.progress["last_state"] = state_abbrev
            self.progress["last_municipality"] = municipality
            self._save_progress()

        print(f"\n{'='*60}")
        print("COLLECTION COMPLETE")
        print(f"Completed: {len(self.progress['completed'])}")
        print(f"Failed: {len(self.progress['failed'])}")
        print(f"{'='*60}")

    def run(self):
        """Run the batch collection process."""
        self.discover_all()
        if not self.discover_only:
            self.collect_all()


if __name__ == "__main__":
    schema = {
        "states": SmartArgItem(
            flags=["--states"],
            prompt="Comma-separated state abbreviations (e.g., 'al,ma,ca') or leave empty for all",
            arg_type=str,
            required=False,
        ),
        "discover_only": SmartArgItem(
            flags=["--discover-only"],
            prompt="Only discover URLs, don't download files",
            action="store_true",
        ),
        "force": SmartArgItem(
            flags=["--force"],
            prompt="Force re-discovery of URLs even if they exist",
            action="store_true",
        ),
        "resume": SmartArgItem(
            flags=["--resume"],
            prompt="Resume from previous progress",
            action="store_true",
        ),
    }
    parser = SmartArgParser(schema)
    args = parser.parse()

    # Parse states if provided
    states = None
    if args.get("states"):
        states = [s.strip() for s in args["states"].split(",")]

    collector = BatchCollector(
        states=states,
        discover_only=args.get("discover_only", False),
        force=args.get("force", False),
    )
    collector.run()
