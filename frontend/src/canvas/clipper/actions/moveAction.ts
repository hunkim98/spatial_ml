import { Point } from "../types/geometry";
import { Action, ActionType } from "./base";

export class MoveAction extends Action {
  _type = ActionType.MOVE;

  constructor(
    private readonly startOffset: Point,
    private readonly endOffset: Point
  ) {
    super();
  }
  createInverseAction(): Action {
    return new MoveAction(this.endOffset, this.startOffset);
  }
}
