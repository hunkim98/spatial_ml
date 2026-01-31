import { Location } from "@/canvas/overlay/types";

export interface MapConfig {
  center?: Location;
  zoom?: number;
}

export interface ImageOverlayConfig {
  opacity?: number;
  visible?: boolean;
}
