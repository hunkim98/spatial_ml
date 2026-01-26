import { Location } from "@/canvas/types";

export interface MapConfig {
  center?: Location;
  zoom?: number;
}

export interface ImageOverlayConfig {
  opacity?: number;
  visible?: boolean;
}
