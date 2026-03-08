import { Point } from "../types";
import { IModel } from "./base";

export interface ImageBufferModelType {
  buffer: HTMLCanvasElement | null;
  width: number | null;
  height: number | null;
  leftTop: Point;
  opacity: number;
}

export class ImageBufferModel extends IModel<ImageBufferModel> {
  // Offscreen canvas buffer (rendered once)
  private _buffer: HTMLCanvasElement | null;

  // Original dimensions
  private _width: number | null;
  private _height: number | null;
  private _leftTop: Point;
  private _opacity: number;

  constructor(props: ImageBufferModelType) {
    super();
    this._buffer = props.buffer;
    this._width = props.width;
    this._height = props.height;
    this._leftTop = props.leftTop;
    this._opacity = props.opacity;
  }

  get buffer(): HTMLCanvasElement | null {
    return this._buffer;
  }
  set buffer(buffer: HTMLCanvasElement | null) {
    this._buffer = buffer;
  }
  get width(): number | null {
    return this._width;
  }
  set width(width: number | null) {
    this._width = width;
  }
  get height(): number | null {
    return this._height;
  }
  set height(height: number | null) {
    this._height = height;
  }
  get leftTop(): Point {
    return this._leftTop;
  }
  set leftTop(leftTop: Point) {
    this._leftTop = leftTop;
  }
  get opacity(): number {
    return this._opacity;
  }
  set opacity(opacity: number) {
    this._opacity = opacity;
  }

  reset() {
    this.buffer = null;
    this.width = null;
    this.height = null;
    this.leftTop = { x: 0, y: 0 };
    this.opacity = 0.5;
  }
}
