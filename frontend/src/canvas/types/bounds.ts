import { Location } from "./location";

export interface Point {
  x: number;
  y: number;
}

export interface ScreenBounds {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface GeoCorners {
  topLeft: Location;
  topRight: Location;
  bottomRight: Location;
  bottomLeft: Location;
}

export interface ScreenCorners {
  topLeft: Point;
  topRight: Point;
  bottomRight: Point;
  bottomLeft: Point;
}

export enum HandleType {
  NONE = "NONE",
  TOP_LEFT = "TOP_LEFT",
  TOP_RIGHT = "TOP_RIGHT",
  BOTTOM_RIGHT = "BOTTOM_RIGHT",
  BOTTOM_LEFT = "BOTTOM_LEFT",
  BODY = "BODY",
}
