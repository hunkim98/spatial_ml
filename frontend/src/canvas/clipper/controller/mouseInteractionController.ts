import { ClipperEventListeners } from "../events";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";

import { addPoints, subtractPoints } from "../utils/math";
import { BaseController } from "./base";
import {
  getCanvasRelativePositionFromWorldPoint,
  getEventRelativePositionToCanvas,
  getWorldPointFromRelativePositionToCanvas,
} from "../utils/project";

type Models = Pick<
  ClipperModel,
  "pdfLayerModel" | "navigationModel" | "mouseInteractionModel"
>;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

type ExecuteParams = {
  e: React.WheelEvent<HTMLCanvasElement> | React.MouseEvent<HTMLCanvasElement>;
};

export class MouseInteractionController extends BaseController<
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

    if (e.type === "wheel") {
      this.executeWheel(e as React.WheelEvent<HTMLCanvasElement>);
    } else if (e.type === "mousedown") {
      this.executeMouseDown(e as React.MouseEvent<HTMLCanvasElement>);
    } else if (e.type === "mousemove") {
      this.executeMouseMove(e as React.MouseEvent<HTMLCanvasElement>);
    } else if (e.type === "mouseup") {
      this.executeMouseUp(e as React.MouseEvent<HTMLCanvasElement>);
    }

    this.views.pdfLayerView.clear();
    this.views.pdfLayerView.render();
    this.views.maskLayerView.render();
  }

  private executeWheel(e: React.WheelEvent<HTMLCanvasElement>): void {
    if (e.ctrlKey) {
      this.zoom(e);
    } else {
      this.pan(e.deltaX, e.deltaY);
    }
  }

  private executeMouseDown(e: React.MouseEvent<HTMLCanvasElement>): void {
    const { element } = this.models.pdfLayerModel;
    if (!this.models.mouseInteractionModel.mouseDownWorldPosition) return;
    const { mouseDownWorldPosition } = this.models.mouseInteractionModel;
    const mouseDownScreenPosition = getEventRelativePositionToCanvas(
      e,
      element
    );
    this.models.mouseInteractionModel.mouseDownScreenPosition =
      mouseDownScreenPosition;
    this.models.mouseInteractionModel.mouseDownWorldPosition =
      mouseDownWorldPosition;
  }

  private executeMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    // Panning is handled by dragInteractionController.
    // This is kept for any future mouse-move tracking needs.
  }

  private executeMouseUp(e: React.MouseEvent<HTMLCanvasElement>): void {
    this.models.mouseInteractionModel.mouseDownScreenPosition = null;
    this.models.mouseInteractionModel.mouseDownWorldPosition = null;
    this.models.mouseInteractionModel.mouseMoveScreenPosition = null;
    this.models.mouseInteractionModel.mouseMoveWorldPosition = null;
  }

  private pan(deltaX: number, deltaY: number): void {
    const newOffset = subtractPoints(this.models.navigationModel.offset, {
      x: deltaX,
      y: deltaY,
    });
    this.models.navigationModel.offset = { x: newOffset.x, y: newOffset.y };
  }

  private zoom(e: React.WheelEvent<HTMLCanvasElement>): void {
    const { scale, minScale, maxScale, offset } = this.models.navigationModel;

    // Normalize deltaY based on deltaMode for consistent behavior
    let normalizedDelta = e.deltaY;
    if (e.deltaMode === 1) normalizedDelta *= 16; // line mode
    if (e.deltaMode === 2) normalizedDelta *= 100; // page mode

    // Exponential zoom: ~5% zoom per scroll unit, feels natural
    const zoomFactor = 1.05;
    const zoom = Math.pow(zoomFactor, -normalizedDelta / 50);
    let newScale = Math.max(minScale, Math.min(maxScale, scale * zoom));

    const { element } = this.models.pdfLayerModel;
    const currentMousePosInCanvas = getEventRelativePositionToCanvas(
      e,
      element
    );
    const currentMouseWorldPos = getWorldPointFromRelativePositionToCanvas(
      currentMousePosInCanvas,
      offset,
      scale
    );
    const nextCurrentMousePosInCanvas = getCanvasRelativePositionFromWorldPoint(
      currentMouseWorldPos,
      offset,
      newScale
    );
    const canvasPosDelta = subtractPoints(
      currentMousePosInCanvas,
      nextCurrentMousePosInCanvas
    );
    const newOffset = addPoints(offset, canvasPosDelta);

    this.models.navigationModel.scale = newScale;
    this.models.navigationModel.offset = { x: newOffset.x, y: newOffset.y };
  }
}
