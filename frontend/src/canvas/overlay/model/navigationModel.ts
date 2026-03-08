import { Point } from "../types";
import { IModel } from "./base";

export type NavigationModelType = {
  scale: number;
  offset: Point;
};

/**
 * NavigationModel - stores canvas pan/zoom state
 */
export class NavigationModel
  extends IModel<NavigationModelType>
  implements NavigationModelType
{
  private _scale: number;
  private _offset: Point;

  constructor(props: NavigationModelType) {
    super();
    this._scale = props.scale;
    this._offset = props.offset;
  }

  get scale(): number {
    return this._scale;
  }

  get offset(): Point {
    return this._offset;
  }

  set scale(f: number) {
    this._scale = f;
  }

  set offset(offset: Point) {
    this._offset = offset;
  }

  reset() {
    this._scale = 1;
    this._offset = { x: 0, y: 0 };
  }
}
