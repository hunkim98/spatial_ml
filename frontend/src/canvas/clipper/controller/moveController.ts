import { BaseController } from "./base";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { ClipperEvent, ClipperEventListeners } from "../events";
import { Point } from "../types";

type Models = Pick<ClipperModel, "clipRectToolModel" | "mouseControlModel">;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

export class MoveController extends BaseController<
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
    switch (params.e.type) {
      case "mousedown":
        this.onMouseDownExecute(params.e);
        break;
      case "mousemove":
        this.onMouseMoveExecute(params.e);
        break;
      case "mouseup":
        this.onMouseUpExecute(params.e);
        break;
    }
  }

  onMouseDownExecute(e: React.MouseEvent<HTMLCanvasElement>): void {
    const mouseDownPosition = this.models.mouseControlModel.mouseDownPosition;
    if (!mouseDownPosition) return;
  }
  onMouseMoveExecute(e: React.MouseEvent<HTMLCanvasElement>): void {}
  onMouseUpExecute(e: React.MouseEvent<HTMLCanvasElement>): void {}

  private onDragStart(point: Point): void {
    const { clipRectToolModel } = this.models;

    clipRectToolModel.dragStart = point;
    clipRectToolModel.rectAtDragStart = clipRectToolModel.rect
      ? { ...clipRectToolModel.rect }
      : null;
  }

  private onDragMove(point: Point): void {
    const { clipRectToolModel } = this.models;
    const { dragStart, rectAtDragStart } = clipRectToolModel;

    if (!dragStart || !rectAtDragStart) return;

    const dx = point.x - dragStart.x;
    const dy = point.y - dragStart.y;

    clipRectToolModel.rect = {
      offset: {
        x: rectAtDragStart.offset.x + dx,
        y: rectAtDragStart.offset.y + dy,
      },
      width: rectAtDragStart.width,
      height: rectAtDragStart.height,
    };

    this.dispatchEvent(ClipperEvent.CLIP_CHANGED);
  }

  private onDragEnd(): void {
    const { clipRectToolModel } = this.models;

    clipRectToolModel.dragStart = null;
    clipRectToolModel.rectAtDragStart = null;
  }
}
