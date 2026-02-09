import { Point } from "../types/geometry";

export const addPoints = (a: Point, b: Point): Point => {
  return {
    x: a.x + b.x,
    y: a.y + b.y,
  };
};

export const subtractPoints = (a: Point, b: Point): Point => {
  return {
    x: a.x - b.x,
    y: a.y - b.y,
  };
};
