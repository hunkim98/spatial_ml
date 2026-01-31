import { StyleSpecification } from "maplibre-gl";
import { Location } from "@/canvas/overlay/types";

export const SATELLITE_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    esri: {
      type: "raster",
      tiles: [
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      ],
      tileSize: 256,
      attribution: "Esri, Maxar, Earthstar Geographics",
    },
  },
  layers: [
    {
      id: "esri-imagery",
      type: "raster",
      source: "esri",
      minzoom: 0,
      maxzoom: 22,
    },
  ],
};

export const DEFAULT_CENTER: Location = {
  lng: -96.0,
  lat: 37.0,
};

export const DEFAULT_ZOOM = 4;

export const IMAGE_SOURCE_ID = "pdf-overlay";
export const IMAGE_LAYER_ID = "pdf-layer";

export const DEFAULT_IMAGE_OPACITY = 0.7;
export const FLY_TO_DURATION = 1500;
export const FIT_BOUNDS_PADDING = 50;
