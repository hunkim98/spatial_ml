#!/usr/bin/env python3
"""
Download GeoJSON from ArcGIS map viewer links and display a preview.

Usage:
    python arcgis_url_to_geojson.py <arcgis_url> [output_file]

Examples:
    python arcgis_url_to_geojson.py "https://boston.maps.arcgis.com/apps/mapviewer/index.html?layers=fffb5de90c814daabf2cfd5538b8d22c"
    python arcgis_url_to_geojson.py "https://boston.maps.arcgis.com/apps/mapviewer/index.html?layers=fffb5de90c814daabf2cfd5538b8d22c" output.geojson

Requirements:
    pip install requests geopandas matplotlib
"""

import json
import os
import platform
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlparse

import requests


def extract_layer_id(url: str) -> tuple[str, str]:
    """Extract the layer ID and base domain from an ArcGIS URL."""
    parsed = urlparse(url)

    # Extract base domain (e.g., boston.maps.arcgis.com)
    base_domain = parsed.netloc

    # Try to extract layer ID from query params
    query_params = parse_qs(parsed.query)

    if "layers" in query_params:
        return base_domain, query_params["layers"][0]

    # Try to extract from path (for direct item URLs)
    # e.g., /home/item.html?id=xxx or /apps/mapviewer/index.html?layers=xxx
    if "id" in query_params:
        return base_domain, query_params["id"][0]

    # Try regex for other URL patterns
    patterns = [
        r"layers=([a-f0-9]{32})",
        r"id=([a-f0-9]{32})",
        r"/items/([a-f0-9]{32})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return base_domain, match.group(1)

    raise ValueError(f"Could not extract layer ID from URL: {url}")


def get_item_info(base_domain: str, layer_id: str) -> dict:
    """Get item metadata from ArcGIS REST API."""
    # Try the portal's sharing API
    url = f"https://{base_domain}/sharing/rest/content/items/{layer_id}"
    params = {"f": "json"}

    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_feature_service_url(item_info: dict) -> str:
    """Extract the feature service URL from item info."""
    if "url" in item_info and item_info["url"]:
        return item_info["url"]

    raise ValueError("Could not find feature service URL in item info")


def query_features_geojson(service_url: str, layer_index: int = 0) -> dict:
    """Query all features from a feature service and return as GeoJSON."""
    # Ensure we're querying a specific layer
    if not service_url.endswith(f"/{layer_index}"):
        if service_url.endswith("/"):
            service_url = f"{service_url}{layer_index}"
        else:
            service_url = f"{service_url}/{layer_index}"

    query_url = f"{service_url}/query"

    all_features = []
    offset = 0
    batch_size = 1000  # ArcGIS typically limits to 1000-2000 per request

    print(f"Querying: {query_url}")

    while True:
        params = {
            "where": "1=1",  # Get all features
            "outFields": "*",  # Get all fields
            "f": "geojson",
            "resultOffset": offset,
            "resultRecordCount": batch_size,
        }

        response = requests.get(query_url, params=params)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            raise ValueError(f"ArcGIS API error: {data['error']}")

        features = data.get("features", [])
        if not features:
            break

        all_features.extend(features)
        print(f"  Downloaded {len(all_features)} features...")

        # Check if we got fewer than requested (means we're done)
        if len(features) < batch_size:
            break

        offset += batch_size

    # Build complete GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": all_features,
    }

    # Preserve CRS if present
    if "crs" in data:
        geojson["crs"] = data["crs"]

    return geojson


def download_arcgis_geojson(url: str) -> tuple[dict, str]:
    """Main function to download GeoJSON from an ArcGIS URL."""
    print(f"Parsing URL: {url}")
    base_domain, layer_id = extract_layer_id(url)
    print(f"  Domain: {base_domain}")
    print(f"  Layer ID: {layer_id}")

    print("Fetching item info...")
    item_info = get_item_info(base_domain, layer_id)
    title = item_info.get("title", "Unknown")
    print(f"  Title: {title}")
    print(f"  Type: {item_info.get('type', 'Unknown')}")

    service_url = get_feature_service_url(item_info)
    print(f"  Service URL: {service_url}")

    print("Downloading features...")
    geojson = query_features_geojson(service_url)
    print(f"  Total features: {len(geojson['features'])}")

    return geojson, title


def plot_geojson(geojson: dict, title: str, output_path: str) -> str:
    """Plot GeoJSON and save as image. Returns the image path."""
    try:
        import geopandas as gpd
        import matplotlib.pyplot as plt
    except ImportError:
        print("Warning: geopandas/matplotlib not installed. Skipping preview.")
        print("  Install with: pip install geopandas matplotlib")
        return None

    print("Generating preview image...")

    # Convert GeoJSON to GeoDataFrame
    gdf = gpd.GeoDataFrame.from_features(geojson["features"])

    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    gdf.plot(ax=ax, edgecolor="black", linewidth=0.3, alpha=0.7)
    ax.set_title(f"{title}\n({len(geojson['features'])} features)", fontsize=12)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")

    # Save image
    image_path = output_path.rsplit(".", 1)[0] + ".png" if output_path else "/tmp/geojson_preview.png"
    plt.savefig(image_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  Preview saved to: {image_path}")
    return image_path


def open_image(image_path: str):
    """Open image with system default viewer."""
    if not image_path or not os.path.exists(image_path):
        return

    # Use absolute path
    image_path = os.path.abspath(image_path)
    print(f"  Opening preview: {image_path}")

    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", image_path], check=True)
        elif system == "Linux":
            subprocess.run(["xdg-open", image_path], check=True)
        elif system == "Windows":
            os.startfile(image_path)
    except Exception as e:
        print(f"  Could not open image automatically: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        geojson, title = download_arcgis_geojson(url)

        if not output_file:
            # Default to project root with sanitized title
            safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            output_file = f"{safe_title}.geojson"

        with open(output_file, "w") as f:
            json.dump(geojson, f)
        print(f"Saved to: {output_file}")

        # Generate and display preview
        image_path = plot_geojson(geojson, title, output_file)
        if image_path:
            open_image(image_path)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
