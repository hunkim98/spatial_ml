export interface Point {
  x: number;
  y: number;
}

export interface Rect {
  offset: Point;
  width: number;
  height: number;
}

export interface PatternCircle {
  id: string;
  name: string; // user-editable; defaults to hex color e.g. "#A3B2C1"
  color: [number, number, number]; // RGB of center pixel
  center: Point; // in image space
  radius: number; // in image space (pixels)
}
