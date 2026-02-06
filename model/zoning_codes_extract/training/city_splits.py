"""
City Splits Manager - Ensures consistent train/val/test splits across models.

This module provides utilities to:
1. Generate city splits once
2. Save splits to a JSON file
3. Load existing splits for reuse

Both the extractor and validator data preparation scripts use this
to ensure they train/test on the same cities.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple


SPLITS_FILENAME = "city_splits.json"


def get_splits_path(output_dir: str) -> Path:
    """Get the path to the city splits file."""
    return Path(output_dir) / SPLITS_FILENAME


def load_splits(output_dir: str) -> Optional[Dict[str, List[str]]]:
    """
    Load existing city splits from file.

    Args:
        output_dir: Directory containing the splits file

    Returns:
        Dictionary with 'train', 'val', 'test' keys mapping to city lists,
        or None if file doesn't exist
    """
    splits_path = get_splits_path(output_dir)

    if not splits_path.exists():
        return None

    with open(splits_path) as f:
        splits = json.load(f)

    print(f"Loaded existing city splits from {splits_path}")
    print(f"  Train: {len(splits['train'])} cities")
    print(f"  Val: {len(splits['val'])} cities")
    print(f"  Test: {len(splits['test'])} cities")

    return splits


def save_splits(splits: Dict[str, List[str]], output_dir: str) -> Path:
    """
    Save city splits to file.

    Args:
        splits: Dictionary with 'train', 'val', 'test' keys
        output_dir: Directory to save the splits file

    Returns:
        Path to the saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    splits_path = get_splits_path(output_dir)

    with open(splits_path, 'w') as f:
        json.dump(splits, f, indent=2)

    print(f"Saved city splits to {splits_path}")

    return splits_path


def generate_splits(
    cities: List[str],
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42
) -> Dict[str, List[str]]:
    """
    Generate new city splits.

    Args:
        cities: List of city identifiers (e.g., "birmingham_alabama")
        train_ratio: Proportion for training
        val_ratio: Proportion for validation
        test_ratio: Proportion for testing
        seed: Random seed for reproducibility

    Returns:
        Dictionary with 'train', 'val', 'test' keys mapping to city lists
    """
    # Set seed for reproducibility
    random.seed(seed)

    # Shuffle cities
    cities = list(cities)  # Make a copy
    random.shuffle(cities)

    # Calculate split indices
    n_cities = len(cities)
    n_train = int(n_cities * train_ratio)
    n_val = int(n_cities * val_ratio)

    # Split
    train_cities = sorted(cities[:n_train])
    val_cities = sorted(cities[n_train:n_train + n_val])
    test_cities = sorted(cities[n_train + n_val:])

    splits = {
        'train': train_cities,
        'val': val_cities,
        'test': test_cities,
        'metadata': {
            'seed': seed,
            'train_ratio': train_ratio,
            'val_ratio': val_ratio,
            'test_ratio': test_ratio,
            'total_cities': n_cities,
        }
    }

    print(f"Generated new city splits (seed={seed}):")
    print(f"  Train: {len(train_cities)} cities")
    print(f"  Val: {len(val_cities)} cities")
    print(f"  Test: {len(test_cities)} cities")

    return splits


def get_or_create_splits(
    cities: List[str],
    output_dir: str,
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    seed: int = 42,
    force_regenerate: bool = False
) -> Dict[str, List[str]]:
    """
    Get existing splits or create new ones.

    This is the main function to use - it ensures consistency by:
    1. Loading existing splits if available
    2. Generating and saving new splits if not

    Args:
        cities: List of all available city identifiers
        output_dir: Directory for the splits file
        train_ratio: Proportion for training (used only if generating)
        val_ratio: Proportion for validation (used only if generating)
        test_ratio: Proportion for testing (used only if generating)
        seed: Random seed (used only if generating)
        force_regenerate: If True, regenerate splits even if file exists

    Returns:
        Dictionary with 'train', 'val', 'test' keys mapping to city lists
    """
    if not force_regenerate:
        existing_splits = load_splits(output_dir)
        if existing_splits is not None:
            # Validate that existing splits are compatible with current cities
            all_split_cities = set(
                existing_splits['train'] +
                existing_splits['val'] +
                existing_splits['test']
            )
            current_cities = set(cities)

            # Check if splits are still valid (all split cities exist in current cities)
            if all_split_cities <= current_cities:
                return existing_splits
            else:
                missing = all_split_cities - current_cities
                print(f"Warning: {len(missing)} cities in splits file no longer available")
                print(f"  Regenerating splits...")

    # Generate new splits
    splits = generate_splits(cities, train_ratio, val_ratio, test_ratio, seed)

    # Save for future use
    save_splits(splits, output_dir)

    return splits


def get_city_key(state: str, city: str) -> str:
    """
    Generate a consistent city key for use in splits.

    Args:
        state: State name or abbreviation
        city: City name

    Returns:
        Normalized city key (e.g., "birmingham_alabama")
    """
    return f"{city.lower().replace(' ', '-')}_{state.lower().replace(' ', '-')}"


def parse_city_key(key: str) -> Tuple[str, str]:
    """
    Parse a city key back into city and state.

    Args:
        key: City key (e.g., "birmingham_alabama")

    Returns:
        Tuple of (city, state)
    """
    parts = key.rsplit('_', 1)
    if len(parts) == 2:
        return parts[0].replace('-', ' '), parts[1].replace('-', ' ')
    return key, ""
