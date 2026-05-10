import { Point } from "../types";

export const addPoints = (a: Point, b: Point): Point => ({
  x: a.x + b.x,
  y: a.y + b.y,
});

export const subtractPoints = (a: Point, b: Point): Point => ({
  x: a.x - b.x,
  y: a.y - b.y,
});

export const distance = (a: Point, b: Point): number => {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.sqrt(dx * dx + dy * dy);
};
