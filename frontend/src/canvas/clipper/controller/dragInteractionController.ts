import { ClipperEventListeners } from "../events";
import { ClipperModel } from "../model";
import { addPoints, subtractPoints } from "../utils/math";
import { ClipperView } from "../view";
import { BaseController } from "./base";

type Models = Pick<
  ClipperModel,
  "mouseInteractionModel" | "dragInteractionModel" | "navigationModel"
>;

type Views = never;

type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

export class DragInteractionController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  constructor(
    models: ClipperModel,
    views: ClipperView,
    listeners: ClipperEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    const { e } = params;
    if (e.type === "mousedown" || e.type === "dragstart") {
      this.executeDragStart(e);
    } else if (e.type === "mousemove" || e.type === "drag") {
      this.executeDragMove(e);
    } else if (e.type === "mouseup" || e.type === "dragend") {
      this.executeDragEnd(e);
    }
  }

  executeDragStart(e: React.MouseEvent<HTMLCanvasElement>): void {
    const { mouseDownScreenPosition } = this.models.mouseInteractionModel;
    if (!mouseDownScreenPosition) return;
    this.models.dragInteractionModel.dragStart = mouseDownScreenPosition;
    this.models.dragInteractionModel.lastDragScreenPoint =
      mouseDownScreenPosition;
  }

  executeDragMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    const { dragStart, lastDragScreenPoint } = this.models.dragInteractionModel;
    const { mouseMoveScreenPosition } = this.models.mouseInteractionModel;
    if (!dragStart || !lastDragScreenPoint || !mouseMoveScreenPosition) return;
    const delta = subtractPoints(mouseMoveScreenPosition, lastDragScreenPoint);
    const newOffset = addPoints(this.models.navigationModel.offset, delta);
    this.models.navigationModel.offset = { x: newOffset.x, y: newOffset.y };
    this.models.dragInteractionModel.lastDragScreenPoint =
      mouseMoveScreenPosition;
  }

  executeDragEnd(e: React.MouseEvent<HTMLCanvasElement>): void {
    this.models.dragInteractionModel.dragStart = null;
  }
}
