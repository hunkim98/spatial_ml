import { Point } from "../types/geometry";
import { IModel } from "./base";

export type NavigationModelType = {
  scale: number;
  offset: Point;
  maxScale: number;
  minScale: number;
  zoomSensitivity: number;
};

export class NavigationModel
  extends IModel<NavigationModelType>
  implements NavigationModelType
{
  private _scale: number;
  private _offset: Point;
  private _maxScale: number;
  private _minScale: number;
  private _zoomSensitivity: number;

  constructor(props: NavigationModelType) {
    super();
    this._scale = props.scale;
    this._offset = props.offset;
    this._maxScale = props.maxScale;
    this._minScale = props.minScale;
    this._zoomSensitivity = props.zoomSensitivity;
  }

  get scale(): number {
    return this._scale;
  }
  get offset(): Point {
    return this._offset;
  }
  get maxScale(): number {
    return this._maxScale;
  }
  get minScale(): number {
    return this._minScale;
  }
  get zoomSensitivity(): number {
    return this._zoomSensitivity;
  }

  /**
   * We will clamp the scale value if it is over the max or below the min
   */
  set scale(f: number) {
    if (f > this.maxScale) {
      this.scale = this.maxScale;
    }
    if (f < this.minScale) {
      this.scale = this.minScale;
    }
    this._scale = f;
  }

  set offset(offset: Point) {
    this._offset = offset;
  }
  set maxScale(maxScale: number) {
    this._maxScale = maxScale;
  }
  set minScale(minScale: number) {
    this._minScale = minScale;
  }
  set zoomSensitivity(zoomSensitivity: number) {
    this._zoomSensitivity = zoomSensitivity;
  }

  reset() {
    this._scale = 1;
    this._offset = { x: 0, y: 0 };
    this._maxScale = 10;
    this._minScale = 0.1;
    this._zoomSensitivity = 1.2;
  }
}
