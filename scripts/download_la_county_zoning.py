#!/usr/bin/env python3
"""Download LA County zoning PDFs."""

import urllib.request
from pathlib import Path

# All unique PDF URLs extracted from the LA County planning website
pdf_urls = [
    # Antelope Valley Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_03a_AV_East.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_03b_AV_South.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_03c_AV_West.pdf",
    # Coastal Islands Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_29_San_Clemente_Island.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_30_Santa_Catalina_Island.pdf",
    # East San Gabriel Valley Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_04_Avocado_Heights.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_05_Charter_Oak_West_San_Dimas.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_06_Covina_Island_East_Irwindale.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_08_East_Azusa_Glendora_Islands.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_12_East_San_Dimas_Northeast_San_Dimas.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_15_Hacienda_Heights.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_23_North_Claremont_Northeast_La_Verne.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_24_North_Pomona_West_Claremont.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_28_Rowland_Heights.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_34_South_Diamond_Bar.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_37_South_San_Jose_Hills_South_Walnut.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_40_Valinda.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_41_Walnut_Islands.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_45_West_Puente_Valley.pdf",
    # Gateway Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_14_Gateway_Islands.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_25_North_Whittier.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_43_West_Carson_Rancho_Dominguez.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_38_South_Whittier-Sunshine_Acres.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_47_West_Whittier-Los_Nietos.pdf",
    # Metro Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_09_East_Los_Angeles.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_11_East_Rancho_Dominguez.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_13_Florence-Firestone_Walnut_Park.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_42_West_Athens-Westmont.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_46_West_Rancho_Dominguez-Victoria.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_50_Willowbrook.pdf",
    # San Fernando Valley Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_16_Kagel_Lopez_Canyons.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_26_Oat_Mountain_Twin_Lakes.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_39_Sylmar_Island.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_48_Westside_Islands.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_44_West_Chatsworth_Westhills.pdf",
    # Santa Clarita Valley Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_31_Santa_Clarita_Valley.pdf",
    # Santa Monica Mountains Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_27_Pepperdine_University.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_32a_Santa_Monica_Mountains_Coastal_Zone_East.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_32b_Santa_Monica_Mountains_Coastal_Zone_West.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_33a_Santa_Monica_Mountains_North_Area_East.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_33b_Santa_Monica_Mountains_North_Area_West.pdf",
    # South Bay Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_01_Alondra_Park_Hawthorne_Island.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_07_Del_Aire.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_19_La_Rambla_Westfield.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_21_Lennox.pdf",
    # West San Gabriel Valley Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_02_Altadena.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_10_East_Pasadena-East_San_Gabriel_San_Pasqual.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_17_Kinneloa_Mesa.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_18_La_Crescenta-Montrose.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_49_Whittier_Narrows_South_El_Monte_Island.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_35_South_Monrovia_Islands.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_36_South_San_Gabriel.pdf",
    # Westside Planning Area
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_20_Ladera_Heights_Viewpark-Windsor_Hills.pdf",
    "https://planning.lacounty.gov/wp-content/uploads/2022/04/map_z_22_Marina_Del_Rey.pdf",
]

# Remove duplicates
pdf_urls = list(set(pdf_urls))

output_dir = Path("/Users/hunkim/Github/spatial_ml/data/maps/CA/la_county/images")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"Downloading {len(pdf_urls)} unique PDFs to {output_dir}")

for url in sorted(pdf_urls):
    filename = url.split("/")[-1]
    output_path = output_dir / filename

    if output_path.exists():
        print(f"Already exists: {filename}")
        continue

    try:
        urllib.request.urlretrieve(url, output_path)
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Failed {filename}: {e}")

print("\nDone!")
