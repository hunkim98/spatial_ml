#!/usr/bin/env python3
"""
Prepare training data from ALL available cities.
Finds cities with both zoneomics CSV and ordinance MD files.
"""

import json
import random
from pathlib import Path
from collections import Counter

# Paths
MUNICODE_DIR = Path('/Users/devraj/Documents/Development/spatial_ml/collector/tmp/zoning_ordinance_md')
ZONEOMICS_DIR = Path('/Users/devraj/Documents/Development/spatial_ml/data/zoneomics')
OUTPUT_DIR = Path(__file__).parent / "data_full"

# State name to abbr mapping
STATE_ABBR = {
    'alabama': 'al', 'alaska': 'ak', 'arizona': 'az', 'arkansas': 'ar',
    'california': 'ca', 'colorado': 'co', 'connecticut': 'ct', 'delaware': 'de',
    'florida': 'fl', 'georgia': 'ga', 'hawaii': 'hi', 'idaho': 'id',
    'illinois': 'il', 'indiana': 'in', 'iowa': 'ia', 'kansas': 'ks',
    'kentucky': 'ky', 'louisiana': 'la', 'maine': 'me', 'maryland': 'md',
    'massachusetts': 'ma', 'michigan': 'mi', 'minnesota': 'mn', 'mississippi': 'ms',
    'missouri': 'mo', 'montana': 'mt', 'nebraska': 'ne', 'nevada': 'nv',
    'new-hampshire': 'nh', 'new-jersey': 'nj', 'new-mexico': 'nm', 'new-york': 'ny',
    'north-carolina': 'nc', 'north-dakota': 'nd', 'ohio': 'oh', 'oklahoma': 'ok',
    'oregon': 'or', 'pennsylvania': 'pa', 'rhode-island': 'ri', 'south-carolina': 'sc',
    'south-dakota': 'sd', 'tennessee': 'tn', 'texas': 'tx', 'utah': 'ut',
    'vermont': 'vt', 'virginia': 'va', 'washington': 'wa', 'west-virginia': 'wv',
    'wisconsin': 'wi', 'wyoming': 'wy'
}

ABBR_TO_STATE = {v: k for k, v in STATE_ABBR.items()}

SEED = 42


def find_matched_cities():
    """Find all cities with both zoneomics and ordinance data."""
    # Get all cities with zoneomics data
    zoneomics_cities = {}
    for state_dir in ZONEOMICS_DIR.iterdir():
        if state_dir.is_dir():
            state_name = state_dir.name
            state_abbr = STATE_ABBR.get(state_name, state_name)
            for csv_file in state_dir.glob('*.csv'):
                city = csv_file.stem
                zoneomics_cities[(state_abbr, city)] = csv_file

    # Get all cities with ordinance data
    municode_cities = {}
    for state_dir in MUNICODE_DIR.iterdir():
        if state_dir.is_dir():
            state_name = state_dir.name
            for city_dir in state_dir.iterdir():
                if city_dir.is_dir() and list(city_dir.glob('*.md')):
                    city = city_dir.name
                    municode_cities[(state_name, city)] = city_dir

    # Find matches
    matched = []
    for (state_abbr, city), csv_path in zoneomics_cities.items():
        # Try different state formats
        for state_format in [state_abbr, state_abbr.upper()]:
            if (state_format, city) in municode_cities:
                matched.append({
                    'city': city,
                    'state': state_abbr,
                    'csv_path': str(csv_path),
                    'ordinance_dir': str(municode_cities[(state_format, city)])
                })
                break
            # Try with hyphens
            city_hyphen = city.replace('_', '-')
            if (state_format, city_hyphen) in municode_cities:
                matched.append({
                    'city': city_hyphen,
                    'state': state_abbr,
                    'csv_path': str(csv_path),
                    'ordinance_dir': str(municode_cities[(state_format, city_hyphen)])
                })
                break

    return matched


def create_splits(matched_cities, test_ratio=0.2):
    """Split cities into train/test with stratification by state."""
    random.seed(SEED)

    # Group by state
    by_state = {}
    for city in matched_cities:
        state = city['state']
        if state not in by_state:
            by_state[state] = []
        by_state[state].append(city)

    train_cities = []
    test_cities = []

    # Stratified split
    for state, cities in by_state.items():
        random.shuffle(cities)
        n_test = max(1, int(len(cities) * test_ratio))
        test_cities.extend(cities[:n_test])
        train_cities.extend(cities[n_test:])

    return train_cities, test_cities


def main():
    print("Finding matched cities...")
    matched = find_matched_cities()
    print(f"Found {len(matched)} cities with both zoneomics and ordinance data")

    # Show distribution
    state_counts = Counter(c['state'] for c in matched)
    print("\nBy state:")
    for state, count in state_counts.most_common():
        print(f"  {state}: {count}")

    # Create splits
    train_cities, test_cities = create_splits(matched)
    print(f"\nSplit: {len(train_cities)} train, {len(test_cities)} test")

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save city splits
    splits = {
        'train': [f"{c['city']}_{c['state']}" for c in train_cities],
        'test': [f"{c['city']}_{c['state']}" for c in test_cities],
        'metadata': {
            'train_cities': [[c['city'], c['state']] for c in train_cities],
            'test_cities': [[c['city'], c['state']] for c in test_cities],
            'train_details': train_cities,
            'test_details': test_cities,
        }
    }

    splits_path = OUTPUT_DIR / "city_splits.json"
    with open(splits_path, 'w') as f:
        json.dump(splits, f, indent=2)
    print(f"\nSaved city splits to {splits_path}")

    # Print test cities
    print("\nTest cities:")
    for c in sorted(test_cities, key=lambda x: (x['state'], x['city'])):
        print(f"  {c['city']}, {c['state']}")


if __name__ == "__main__":
    main()
