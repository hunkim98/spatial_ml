import { Point } from "./geometry";

export interface ClipRect {
  offset: Point;
  width: number;
  height: number;
}

export enum HandleType {
  NONE = "NONE",
  TOP_LEFT = "TOP_LEFT",
  TOP_RIGHT = "TOP_RIGHT",
  BOTTOM_RIGHT = "BOTTOM_RIGHT",
  BOTTOM_LEFT = "BOTTOM_LEFT",
  LEFT = "LEFT",
  RIGHT = "RIGHT",
  TOP = "TOP",
  BOTTOM = "BOTTOM",
  BODY = "BODY",
}
