import { PatternSelectorEventListeners } from "../events";
import { PatternSelectorModel } from "../model";
import { PatternSelectorView } from "../view";
import { addPoints, subtractPoints } from "../utils/math";
import { BaseController } from "./base";

type Models = Pick<
  PatternSelectorModel,
  | "mouseInteractionModel"
  | "dragInteractionModel"
  | "navigationModel"
  | "patternCirclesModel"
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
    models: PatternSelectorModel,
    views: PatternSelectorView,
    listeners: PatternSelectorEventListeners
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

  private executeDragStart(): void {
    // Only pan when space is held (isCreating === false and no active tool)
    if (this.models.patternCirclesModel.isCreating) return;

    const { mouseDownScreenPosition } = this.models.mouseInteractionModel;
    if (!mouseDownScreenPosition) return;
    this.models.dragInteractionModel.dragStartWorldPosition =
      mouseDownScreenPosition;
    this.models.dragInteractionModel.lastDragScreenPosition =
      mouseDownScreenPosition;
  }

  private executeDragMove(): void {
    if (this.models.patternCirclesModel.isCreating) return;

    const {
      dragStartWorldPosition: dragStart,
      lastDragScreenPosition: lastDragScreenPoint,
    } = this.models.dragInteractionModel;
    const { mouseMoveScreenPosition } = this.models.mouseInteractionModel;
    if (!dragStart || !lastDragScreenPoint || !mouseMoveScreenPosition) return;
    const delta = subtractPoints(mouseMoveScreenPosition, lastDragScreenPoint);
    const newOffset = addPoints(this.models.navigationModel.offset, delta);
    this.models.navigationModel.offset = { x: newOffset.x, y: newOffset.y };
    this.models.dragInteractionModel.lastDragScreenPosition =
      mouseMoveScreenPosition;
  }

  private executeDragEnd(): void {
    this.models.dragInteractionModel.dragStartWorldPosition = null;
    this.models.dragInteractionModel.lastDragScreenPosition = null;
  }
}
