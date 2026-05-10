import { PatternSelectorEventListeners } from "../events";
import { PatternSelectorModel } from "../model";
import { PatternSelectorView } from "../view";
import { addPoints, subtractPoints } from "../utils/math";
import { BaseController } from "./base";
import {
  getCanvasRelativePositionFromWorldPoint,
  getEventRelativePositionToCanvas,
  getWorldPointFromRelativePositionToCanvas,
} from "../utils/project";

type Models = Pick<
  PatternSelectorModel,
  "imageLayerModel" | "navigationModel" | "mouseInteractionModel"
>;
type Views = Pick<
  PatternSelectorView,
  "imageLayerView" | "overlayLayerView"
>;

type ExecuteParams = {
  e: React.WheelEvent<HTMLCanvasElement> | React.MouseEvent<HTMLCanvasElement>;
};

export class MouseInteractionController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  constructor(
    models: PatternSelectorModel,
    views: PatternSelectorView,
    listeners: PatternSelectorEventListeners
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
      // Mouse move tracking handled externally
    } else if (e.type === "mouseup") {
      this.executeMouseUp();
    }

    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.overlayLayerView.render();
  }

  private executeMouseDown(e: React.MouseEvent<HTMLCanvasElement>): void {
    const { element } = this.models.imageLayerModel;
    if (!this.models.mouseInteractionModel.mouseDownWorldPosition) return;
    const mouseDownScreenPosition = getEventRelativePositionToCanvas(
      e,
      element
    );
    this.models.mouseInteractionModel.mouseDownScreenPosition =
      mouseDownScreenPosition;
  }

  private executeMouseUp(): void {
    this.models.mouseInteractionModel.mouseDownScreenPosition = null;
    this.models.mouseInteractionModel.mouseDownWorldPosition = null;
    this.models.mouseInteractionModel.mouseMoveScreenPosition = null;
    this.models.mouseInteractionModel.mouseMoveWorldPosition = null;
  }

  private executeWheel(e: React.WheelEvent<HTMLCanvasElement>): void {
    if (e.ctrlKey) {
      this.zoom(e);
    } else {
      this.pan(e.deltaX, e.deltaY);
    }
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

    let normalizedDelta = e.deltaY;
    if (e.deltaMode === 1) normalizedDelta *= 16;
    if (e.deltaMode === 2) normalizedDelta *= 100;

    const zoomFactor = 1.05;
    const zoom = Math.pow(zoomFactor, -normalizedDelta / 50);
    const newScale = Math.max(minScale, Math.min(maxScale, scale * zoom));

    const { element } = this.models.imageLayerModel;
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
