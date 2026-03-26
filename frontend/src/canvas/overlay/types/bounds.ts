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
  corner1: Location;
  corner2: Location;
  corner3: Location;
  corner4: Location;
}

export interface ScreenCorners {
  corner1: Point;
  corner2: Point;
  corner3: Point;
  corner4: Point;
}

export enum HandleType {
  NONE = "NONE",
  TOP_LEFT = "TOP_LEFT",
  TOP_RIGHT = "TOP_RIGHT",
  BOTTOM_RIGHT = "BOTTOM_RIGHT",
  BOTTOM_LEFT = "BOTTOM_LEFT",
  TOP_EDGE = "TOP_EDGE",
  RIGHT_EDGE = "RIGHT_EDGE",
  BOTTOM_EDGE = "BOTTOM_EDGE",
  LEFT_EDGE = "LEFT_EDGE",
  CUSTOM_ANCHOR = "CUSTOM_ANCHOR",
  BODY = "BODY",
}

export enum EditorMode {
  VIEW = "VIEW",
  EDIT = "EDIT",
}
