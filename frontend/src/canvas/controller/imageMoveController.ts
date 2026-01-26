import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEvent, CanvasEventListeners } from "../events";
import { Point, DragParams } from "../types";

type Models = Pick<CanvasModel, "transformModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

export class ImageMoveController extends BaseController<
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

    transformModel.dragStart = point;
    transformModel.cornersAtDragStart = transformModel.corners
      ? { ...transformModel.corners }
      : null;
  }

  private onDragMove(point: Point): void {
    const { transformModel } = this.models;
    const { dragStart, cornersAtDragStart } = transformModel;

    if (!dragStart || !cornersAtDragStart) return;

    const dx = point.x - dragStart.x;
    const dy = point.y - dragStart.y;

    transformModel.corners = {
      topLeft: {
        x: cornersAtDragStart.topLeft.x + dx,
        y: cornersAtDragStart.topLeft.y + dy,
      },
      topRight: {
        x: cornersAtDragStart.topRight.x + dx,
        y: cornersAtDragStart.topRight.y + dy,
      },
      bottomRight: {
        x: cornersAtDragStart.bottomRight.x + dx,
        y: cornersAtDragStart.bottomRight.y + dy,
      },
      bottomLeft: {
        x: cornersAtDragStart.bottomLeft.x + dx,
        y: cornersAtDragStart.bottomLeft.y + dy,
      },
    };

    this.dispatchEvent(CanvasEvent.TRANSFORM_CHANGED);
  }

  private onDragEnd(): void {
    const { transformModel } = this.models;

    transformModel.dragStart = null;
    transformModel.cornersAtDragStart = null;
  }
}
