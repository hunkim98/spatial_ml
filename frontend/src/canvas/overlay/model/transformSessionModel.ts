import { Point } from "../types";
import { IModel } from "./base";

export class TransformSessionModel extends IModel<TransformSessionModel> {
  isActive: boolean = false;
  savedScale: number | null = null;
  savedOffset: Point | null = null;

  reset() {
    this.isActive = false;
    this.savedScale = null;
    this.savedOffset = null;
  }
}
