import { Point, HandleType } from "./bounds";

export type InteractionType = "start" | "move" | "end";

export interface DragParams {
  type: InteractionType;
  point: Point;
}

export interface ScaleParams {
  type: InteractionType;
  point: Point;
  handle: HandleType;
}

export interface RotateParams {
  type: InteractionType;
  point: Point;
}
