import { Map } from "maplibre-gl";
import { Location } from "@/canvas/overlay/types";
import { FLY_TO_DURATION, FIT_BOUNDS_PADDING } from "../config";

export class NavigationController {
  private map: Map | null = null;

  setMap(map: Map): void {
    this.map = map;
  }

  flyTo(center: Location, zoom: number = 12): void {
    this.map?.flyTo({
      center: [center.lng, center.lat],
      zoom,
      duration: FLY_TO_DURATION,
    });
  }

  fitBounds(
    bounds: [number, number, number, number],
    padding: number = FIT_BOUNDS_PADDING
  ): void {
    if (!this.map) return;

    // bounds: [south, north, west, east]
    this.map.fitBounds(
      [
        [bounds[2], bounds[0]], // southwest
        [bounds[3], bounds[1]], // northeast
      ],
      { padding, duration: 1500 }
    );
  }

  setZoom(zoom: number): void {
    this.map?.setZoom(zoom);
  }

  getZoom(): number {
    return this.map?.getZoom() ?? 0;
  }

  setCenter(center: Location): void {
    this.map?.setCenter([center.lng, center.lat]);
  }

  getCenter(): Location {
    const center = this.map?.getCenter();

    return center ? { lng: center.lng, lat: center.lat } : { lng: 0, lat: 0 };
  }
}
