import { Map } from "maplibre-gl";
import {
  Location,
  GeoCorners,
  ScreenCorners,
  Point,
} from "@/canvas/overlay/types";

export class ProjectionController {
  private map: Map | null = null;

  setMap(map: Map): void {
    this.map = map;
  }

  project(location: Location): Point {
    if (!this.map) return { x: 0, y: 0 };

    const point = this.map.project([location.lng, location.lat]);

    return { x: point.x, y: point.y };
  }

  unproject(point: Point): Location {
    if (!this.map) return { lng: 0, lat: 0 };

    const lngLat = this.map.unproject([point.x, point.y]);

    return { lng: lngLat.lng, lat: lngLat.lat };
  }

  projectCorners(geoCorners: GeoCorners): ScreenCorners {
    return {
      corner1: this.project(geoCorners.corner1),
      corner2: this.project(geoCorners.corner2),
      corner4: this.project(geoCorners.corner4),
      corner3: this.project(geoCorners.corner3),
    };
  }

  unprojectCorners(screenCorners: ScreenCorners): GeoCorners {
    return {
      corner1: this.unproject(screenCorners.corner1),
      corner2: this.unproject(screenCorners.corner2),
      corner4: this.unproject(screenCorners.corner4),
      corner3: this.unproject(screenCorners.corner3),
    };
  }
}
