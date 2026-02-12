import { Map, MapOptions } from "maplibre-gl";
import {
  ProjectionController,
  ImageSourceController,
  NavigationController,
} from "./controller";
import { SATELLITE_STYLE, DEFAULT_CENTER, DEFAULT_ZOOM } from "./config";
import { MapConfig } from "./types";

export class MapManager {
  private map: Map | null = null;

  readonly projection: ProjectionController;
  readonly imageSource: ImageSourceController;
  readonly navigation: NavigationController;

  constructor() {
    this.projection = new ProjectionController();
    this.imageSource = new ImageSourceController();
    this.navigation = new NavigationController();
  }

  async initialize(container: HTMLDivElement, config?: MapConfig): Promise<Map> {
    const options: MapOptions = {
      container,
      style: SATELLITE_STYLE,
      center: config?.center
        ? [config.center.lng, config.center.lat]
        : [DEFAULT_CENTER.lng, DEFAULT_CENTER.lat],
      zoom: config?.zoom ?? DEFAULT_ZOOM,
      maxPitch: 0,
    };

    this.map = new Map(options);

    return new Promise((resolve) => {
      this.map!.on("load", () => {
        this.projection.setMap(this.map!);
        this.imageSource.setMap(this.map!);
        this.navigation.setMap(this.map!);
        resolve(this.map!);
      });
    });
  }

  getMap(): Map | null {
    return this.map;
  }

  onMove(callback: () => void): void {
    this.map?.on("move", callback);
  }

  offMove(callback: () => void): void {
    this.map?.off("move", callback);
  }

  lockInteractions(): void {
    if (!this.map) return;

    this.map.scrollZoom.disable();
    this.map.dragPan.disable();
    this.map.dragRotate.disable();
    this.map.doubleClickZoom.disable();
    this.map.touchZoomRotate.disable();
  }

  unlockInteractions(): void {
    if (!this.map) return;

    this.map.scrollZoom.enable();
    this.map.dragPan.enable();
    this.map.dragRotate.enable();
    this.map.doubleClickZoom.enable();
    this.map.touchZoomRotate.enable();
  }

  destroy(): void {
    this.map?.remove();
    this.map = null;
  }
}
