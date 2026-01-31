import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEvent, CanvasEventListeners } from "../events";
import { Point, DragParams } from "../types";

type Models = Pick<CanvasModel, "transformModel" | "imageBufferModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

export class ImageCreateController extends BaseController<
  Models,
  Views,
  DragParams
> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: DragParams): void {
    switch (params.type) {
      case "start":
        this.onDragStart(params.point);
        break;
      case "move":
        this.onDragMove(params.point);
        break;
      case "end":
        this.onDragEnd();
        break;
    }
  }

  private onDragStart(point: Point): void {
    const { transformModel } = this.models;

    // Store the anchor point as dragStart
    transformModel.dragStart = point;

    // Initialize corners with zero-size rect at anchor
    transformModel.corners = {
      topLeft: { x: point.x, y: point.y },
      topRight: { x: point.x, y: point.y },
      bottomRight: { x: point.x, y: point.y },
      bottomLeft: { x: point.x, y: point.y },
    };
  }

  private onDragMove(point: Point): void {
    const { transformModel, imageBufferModel } = this.models;
    const { dragStart } = transformModel;

    if (!dragStart) return;

    // Calculate the bounding box from anchor to current point
    const minX = Math.min(dragStart.x, point.x);
    const maxX = Math.max(dragStart.x, point.x);
    const minY = Math.min(dragStart.y, point.y);
    const maxY = Math.max(dragStart.y, point.y);

    // Maintain aspect ratio based on the buffer dimensions
    const bufferWidth = imageBufferModel.width;
    const bufferHeight = imageBufferModel.height;

    if (bufferWidth > 0 && bufferHeight > 0) {
      const aspectRatio = bufferWidth / bufferHeight;
      let width = maxX - minX;
      let height = maxY - minY;

      // Adjust to maintain aspect ratio
      const currentRatio = width / height;

      if (currentRatio > aspectRatio) {
        // Width is too large, adjust based on height
        width = height * aspectRatio;
      } else {
        // Height is too large, adjust based on width
        height = width / aspectRatio;
      }

      // Determine which corner is the anchor and position accordingly
      let x1: number, y1: number, x2: number, y2: number;

      if (dragStart.x <= point.x && dragStart.y <= point.y) {
        // Dragging from top-left to bottom-right
        x1 = dragStart.x;
        y1 = dragStart.y;
        x2 = dragStart.x + width;
        y2 = dragStart.y + height;
      } else if (dragStart.x >= point.x && dragStart.y <= point.y) {
        // Dragging from top-right to bottom-left
        x2 = dragStart.x;
        y1 = dragStart.y;
        x1 = dragStart.x - width;
        y2 = dragStart.y + height;
      } else if (dragStart.x <= point.x && dragStart.y >= point.y) {
        // Dragging from bottom-left to top-right
        x1 = dragStart.x;
        y2 = dragStart.y;
        x2 = dragStart.x + width;
        y1 = dragStart.y - height;
      } else {
        // Dragging from bottom-right to top-left
        x2 = dragStart.x;
        y2 = dragStart.y;
        x1 = dragStart.x - width;
        y1 = dragStart.y - height;
      }

      transformModel.corners = {
        topLeft: { x: x1, y: y1 },
        topRight: { x: x2, y: y1 },
        bottomRight: { x: x2, y: y2 },
        bottomLeft: { x: x1, y: y2 },
      };
    }
  }

  private onDragEnd(): void {
    const { transformModel } = this.models;

    transformModel.dragStart = null;

    // Dispatch event to notify that bounds have been created
    this.dispatchEvent(CanvasEvent.BOUNDS_CREATED);
  }
}
