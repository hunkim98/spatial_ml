import { IModel } from "./base";
import { Point } from "../types/geometry";

export type MouseControlModelType = {
  _mouseDownPosition: Point | null;
  _mouseMovePosition: Point | null;
  _mouseUpPosition: Point | null;
};

export class MouseControlModel extends IModel<MouseControlModelType> {
  _mouseDownPosition: Point | null;
  _mouseMovePosition: Point | null;
  _mouseUpPosition: Point | null;

  constructor() {
    super();
    this._mouseDownPosition = null;
    this._mouseMovePosition = null;
    this._mouseUpPosition = null;
  }

  get mouseDownPosition(): Point | null {
    return this._mouseDownPosition;
  }
  set mouseDownPosition(position: Point | null) {
    this._mouseDownPosition = position;
  }
  get mouseMovePosition(): Point | null {
    return this._mouseMovePosition;
  }
  set mouseMovePosition(position: Point | null) {
    this._mouseMovePosition = position;
  }
  get mouseUpPosition(): Point | null {
    return this._mouseUpPosition;
  }
  set mouseUpPosition(position: Point | null) {
    this._mouseUpPosition = position;
  }

  reset() {
    this._mouseDownPosition = null;
    this._mouseMovePosition = null;
    this._mouseUpPosition = null;
  }
}
