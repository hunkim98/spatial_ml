import { Map } from "maplibre-gl";
import { Location, GeoCorners, ScreenCorners, Point } from "@/canvas/types";

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
      topLeft: this.project(geoCorners.topLeft),
      topRight: this.project(geoCorners.topRight),
      bottomRight: this.project(geoCorners.bottomRight),
      bottomLeft: this.project(geoCorners.bottomLeft),
    };
  }

  unprojectCorners(screenCorners: ScreenCorners): GeoCorners {
    return {
      topLeft: this.unproject(screenCorners.topLeft),
      topRight: this.unproject(screenCorners.topRight),
      bottomRight: this.unproject(screenCorners.bottomRight),
      bottomLeft: this.unproject(screenCorners.bottomLeft),
    };
  }
}
