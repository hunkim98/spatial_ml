import { Map, ImageSource } from "maplibre-gl";
import { GeoCorners } from "@/canvas/overlay/types";
import {
  IMAGE_SOURCE_ID,
  IMAGE_LAYER_ID,
  DEFAULT_IMAGE_OPACITY,
} from "../config";

export class ImageSourceController {
  private map: Map | null = null;

  setMap(map: Map): void {
    this.map = map;
  }

  add(
    imageUrl: string,
    corners: GeoCorners,
    opacity: number = DEFAULT_IMAGE_OPACITY
  ): void {
    if (!this.map) return;

    this.remove();

    this.map.addSource(IMAGE_SOURCE_ID, {
      type: "image",
      url: imageUrl,
      coordinates: this.toCoordinates(corners),
    });

    this.map.addLayer({
      id: IMAGE_LAYER_ID,
      type: "raster",
      source: IMAGE_SOURCE_ID,
      paint: { "raster-opacity": opacity },
    });
  }

  update(corners: GeoCorners): void {
    if (!this.map) return;

    const source = this.map.getSource(IMAGE_SOURCE_ID) as ImageSource;

    if (source) {
      source.setCoordinates(this.toCoordinates(corners));
    }
  }

  remove(): void {
    if (!this.map) return;

    if (this.map.getLayer(IMAGE_LAYER_ID)) {
      this.map.removeLayer(IMAGE_LAYER_ID);
    }

    if (this.map.getSource(IMAGE_SOURCE_ID)) {
      this.map.removeSource(IMAGE_SOURCE_ID);
    }
  }

  setVisibility(visible: boolean): void {
    if (!this.map || !this.map.getLayer(IMAGE_LAYER_ID)) return;

    this.map.setLayoutProperty(
      IMAGE_LAYER_ID,
      "visibility",
      visible ? "visible" : "none"
    );
  }

  setOpacity(opacity: number): void {
    if (!this.map || !this.map.getLayer(IMAGE_LAYER_ID)) return;

    this.map.setPaintProperty(IMAGE_LAYER_ID, "raster-opacity", opacity);
  }

  exists(): boolean {
    return this.map?.getSource(IMAGE_SOURCE_ID) !== undefined;
  }

  private toCoordinates(
    corners: GeoCorners
  ): [[number, number], [number, number], [number, number], [number, number]] {
    return [
      [corners.corner1.lng, corners.corner1.lat],
      [corners.corner2.lng, corners.corner2.lat],
      [corners.corner4.lng, corners.corner4.lat],
      [corners.corner3.lng, corners.corner3.lat],
    ];
  }
}
