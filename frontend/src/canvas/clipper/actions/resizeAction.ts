import { Action, ActionType } from "./base";
import { ClipRect } from "../types";

export class ResizeAction extends Action {
  _type = ActionType.RESIZE;

  constructor(
    private readonly startWidthHeight: [number, number],
    private readonly endWidthHeight: [number, number]
  ) {
    super();
  }
  createInverseAction(): Action {
    return new ResizeAction(this.endWidthHeight, this.startWidthHeight);
  }
}
