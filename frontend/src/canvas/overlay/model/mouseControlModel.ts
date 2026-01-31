import { IModel } from "./base";
import { Point } from "../types";

export class MouseControlModel extends IModel<MouseControlModel> {
  position: Point = { x: 0, y: 0 };
  isDown: boolean = false;

  reset() {
    this.position = { x: 0, y: 0 };
    this.isDown = false;
  }
}
