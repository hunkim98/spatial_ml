import { ClipperEventListeners } from "../events";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import {
  getEventRelativePositionToCanvas,
  getWorldPointFromRelativePositionToCanvas,
  getCanvasRelativePositionFromWorldPoint,
} from "../utils/event";
import { addPoints, subtractPoints } from "../utils/math";
import { BaseController } from "./base";

type Models = Pick<
  ClipperModel,
  "pdfLayerModel" | "navigationModel" | "mouseControlModel"
>;
type Views = Pick<ClipperView, "pdfLayerView" | "maskLayerView">;

type ExecuteParams = {
  e:
    | React.WheelEvent<HTMLCanvasElement>
    | React.MouseEvent<HTMLCanvasElement>;
};

export class PanZoomController extends BaseController<
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
    const pos = getEventRelativePositionToCanvas(e, element);
    this.models.mouseControlModel.mouseDownPosition = pos;
  }

  private executeMouseMove(e: React.MouseEvent<HTMLCanvasElement>): void {
    const { mouseDownPosition } = this.models.mouseControlModel;
    if (!mouseDownPosition) return;

    const { element } = this.models.pdfLayerModel;
    const currentPos = getEventRelativePositionToCanvas(e, element);
    const delta = subtractPoints(currentPos, mouseDownPosition);

    const newOffset = addPoints(this.models.navigationModel.offset, delta);
    this.models.navigationModel.offset = { x: newOffset.x, y: newOffset.y };

    this.models.mouseControlModel.mouseDownPosition = currentPos;
  }

  private pan(deltaX: number, deltaY: number): void {
    const newOffset = subtractPoints(this.models.navigationModel.offset, {
      x: deltaX,
      y: deltaY,
    });
    this.models.navigationModel.offset = { x: newOffset.x, y: newOffset.y };
  }

  private zoom(e: React.WheelEvent<HTMLCanvasElement>): void {
    const { zoomSensitivity, scale, minScale, maxScale, offset } =
      this.models.navigationModel;

    const zoom = 1 - e.deltaY / zoomSensitivity;
    let newScale = scale * zoom;

    if (newScale < minScale) {
      newScale = minScale;
    }
    if (newScale > maxScale) {
      newScale = maxScale;
    }

    const { element } = this.models.pdfLayerModel;
    const currentMousePosInCanvas = getEventRelativePositionToCanvas(e, element);
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
