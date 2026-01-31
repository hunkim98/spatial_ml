import { BaseController } from "./base";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { ClipperEvent, ClipperEventListeners } from "../events";
import { Point, HandleType, ClipRect } from "../types";

type Models = Pick<ClipperModel, "clipRectToolModel" | "mouseControlModel">;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

export class ResizeController extends BaseController<Models, Views, ExecuteParams> {
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

  private onResizeStart(point: Point, handle: HandleType): void {
    const { clipRectToolModel } = this.models;

    clipRectToolModel.activeHandle = handle;
    clipRectToolModel.dragStart = point;
    clipRectToolModel.rectAtDragStart = clipRectToolModel.rect
      ? { ...clipRectToolModel.rect }
      : null;
  }

  private onResizeMove(point: Point): void {
    const { clipRectToolModel } = this.models;
    const { dragStart, rectAtDragStart, activeHandle } = clipRectToolModel;

    if (!dragStart || !rectAtDragStart || activeHandle === HandleType.NONE) {
      return;
    }

    const newRect = this.calculateNewRect(rectAtDragStart, point, activeHandle);
    clipRectToolModel.rect = newRect;

    this.dispatchEvent(ClipperEvent.CLIP_CHANGED);
  }

  private onResizeEnd(): void {
    const { clipRectToolModel } = this.models;

    clipRectToolModel.activeHandle = HandleType.NONE;
    clipRectToolModel.dragStart = null;
    clipRectToolModel.rectAtDragStart = null;
  }

  private calculateNewRect(
    originalRect: ClipRect,
    currentPoint: Point,
    handle: HandleType
  ): ClipRect {
    let x = originalRect.offset.x;
    let y = originalRect.offset.y;
    let { width, height } = originalRect;

    switch (handle) {
      case HandleType.TOP_LEFT: {
        // Anchor is bottom-right
        const anchorX = originalRect.offset.x + originalRect.width;
        const anchorY = originalRect.offset.y + originalRect.height;
        x = Math.min(currentPoint.x, anchorX);
        y = Math.min(currentPoint.y, anchorY);
        width = Math.abs(anchorX - currentPoint.x);
        height = Math.abs(anchorY - currentPoint.y);
        break;
      }
      case HandleType.TOP_RIGHT: {
        // Anchor is bottom-left
        const anchorX = originalRect.offset.x;
        const anchorY = originalRect.offset.y + originalRect.height;
        x = Math.min(currentPoint.x, anchorX);
        y = Math.min(currentPoint.y, anchorY);
        width = Math.abs(currentPoint.x - anchorX);
        height = Math.abs(anchorY - currentPoint.y);
        break;
      }
      case HandleType.BOTTOM_RIGHT: {
        // Anchor is top-left
        const anchorX = originalRect.offset.x;
        const anchorY = originalRect.offset.y;
        x = Math.min(currentPoint.x, anchorX);
        y = Math.min(currentPoint.y, anchorY);
        width = Math.abs(currentPoint.x - anchorX);
        height = Math.abs(currentPoint.y - anchorY);
        break;
      }
      case HandleType.BOTTOM_LEFT: {
        // Anchor is top-right
        const anchorX = originalRect.offset.x + originalRect.width;
        const anchorY = originalRect.offset.y;
        x = Math.min(currentPoint.x, anchorX);
        y = Math.min(currentPoint.y, anchorY);
        width = Math.abs(anchorX - currentPoint.x);
        height = Math.abs(currentPoint.y - anchorY);
        break;
      }
    }

    return { offset: { x, y }, width, height };
  }
}
