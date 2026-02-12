import { CanvasEventListeners } from "../events";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { BaseController } from "./base";
import { ToolType } from "../model/tools/toolManagerModel";

type Models = Pick<
  CanvasModel,
  | "mouseInteractionModel"
  | "dragInteractionModel"
  | "navigationModel"
  | "toolManagerModel"
>;

type Views = never;

type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

export class DragInteractionController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    const { e } = params;
    if (e.type === "mousedown" || e.type === "dragstart") {
      this.executeDragStart();
    } else if (e.type === "mousemove" || e.type === "drag") {
      this.executeDragMove();
    } else if (e.type === "mouseup" || e.type === "dragend") {
      this.executeDragEnd();
    }
  }

  executeDragStart(): void {
    const activeTool = this.models.toolManagerModel.activeTool;
    // Don't handle drag when creating or transforming image
    if (
      activeTool === ToolType.IMAGE_CREATE ||
      activeTool === ToolType.IMAGE_MOVE ||
      activeTool === ToolType.IMAGE_RESIZE ||
      activeTool === ToolType.IMAGE_ROTATE
    ) {
      return;
    }
    const { mouseDownScreenPosition } = this.models.mouseInteractionModel;
    if (!mouseDownScreenPosition) return;
    this.models.dragInteractionModel.dragStartWorldPosition =
      mouseDownScreenPosition;
    this.models.dragInteractionModel.lastDragScreenPosition =
      mouseDownScreenPosition;
  }

  executeDragMove(): void {
    const activeTool = this.models.toolManagerModel.activeTool;
    // Don't handle drag when creating or transforming image
    if (
      activeTool === ToolType.IMAGE_CREATE ||
      activeTool === ToolType.IMAGE_MOVE ||
      activeTool === ToolType.IMAGE_RESIZE ||
      activeTool === ToolType.IMAGE_ROTATE
    ) {
      return;
    }
    // Panning is handled by the map component underneath
    // This is kept for consistency with clipper pattern
  }

  executeDragEnd(): void {
    this.models.dragInteractionModel.dragStartWorldPosition = null;
  }
}
