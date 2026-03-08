import { IModel } from "./base";
import { Point } from "../types/geometry";

export type MouseInteractionModelType = {
  mouseDownWorldPosition: Point | null;
  mouseDownScreenPosition: Point | null;
  mouseMoveWorldPosition: Point | null;
  mouseMoveScreenPosition: Point | null;
  mouseUpWorldPosition: Point | null;
  mouseUpScreenPosition: Point | null;
};

export class MouseInteractionModel
  extends IModel<MouseInteractionModelType>
  implements MouseInteractionModelType
{
  private _mouseDownWorldPosition: Point | null;
  private _mouseDownScreenPosition: Point | null;
  private _mouseMoveWorldPosition: Point | null;
  private _mouseMoveScreenPosition: Point | null;
  private _mouseUpWorldPosition: Point | null;
  private _mouseUpScreenPosition: Point | null;

  constructor() {
    super();
    this._mouseDownWorldPosition = null;
    this._mouseDownScreenPosition = null;
    this._mouseMoveWorldPosition = null;
    this._mouseMoveScreenPosition = null;
    this._mouseUpWorldPosition = null;
    this._mouseUpScreenPosition = null;
  }

  get mouseDownWorldPosition(): Point | null {
    return this._mouseDownWorldPosition;
  }
  set mouseDownWorldPosition(position: Point | null) {
    this._mouseDownWorldPosition = position;
  }

  get mouseDownScreenPosition(): Point | null {
    return this._mouseDownScreenPosition;
  }
  set mouseDownScreenPosition(position: Point | null) {
    this._mouseDownScreenPosition = position;
  }

  get mouseMoveWorldPosition(): Point | null {
    return this._mouseMoveWorldPosition;
  }
  set mouseMoveWorldPosition(position: Point | null) {
    this._mouseMoveWorldPosition = position;
  }

  get mouseMoveScreenPosition(): Point | null {
    return this._mouseMoveScreenPosition;
  }
  set mouseMoveScreenPosition(position: Point | null) {
    this._mouseMoveScreenPosition = position;
  }

  get mouseUpWorldPosition(): Point | null {
    return this._mouseUpWorldPosition;
  }
  set mouseUpWorldPosition(position: Point | null) {
    this._mouseUpWorldPosition = position;
  }

  get mouseUpScreenPosition(): Point | null {
    return this._mouseUpScreenPosition;
  }
  set mouseUpScreenPosition(position: Point | null) {
    this._mouseUpScreenPosition = position;
  }

  reset() {
    this._mouseDownWorldPosition = null;
    this._mouseDownScreenPosition = null;
    this._mouseMoveWorldPosition = null;
    this._mouseMoveScreenPosition = null;
    this._mouseUpWorldPosition = null;
    this._mouseUpScreenPosition = null;
  }
}
