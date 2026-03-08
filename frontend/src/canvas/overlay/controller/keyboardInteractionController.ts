import { CanvasEventListeners } from "../events";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { BaseController } from "./base";

type Models = Pick<
  CanvasModel,
  "keyboardInteractionModel" | "toolManagerModel"
>;
type Views = Pick<CanvasView, never>;

type ExecuteParams = {
  e: KeyboardEvent;
};

export class KeyboardInteractionController extends BaseController<
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

    if (e.type === "keydown") {
      this.executeKeyDown(e);
    } else if (e.type === "keyup") {
      this.executeKeyUp(e);
    }
  }

  private executeKeyDown(e: KeyboardEvent): void {
    if (e.code === "Space") {
      this.models.keyboardInteractionModel.spaceHeld = true;
      // null means the grab tool is active
      this.models.toolManagerModel.activeTool = null;
    }
  }

  private executeKeyUp(e: KeyboardEvent): void {
    if (e.code === "Space") {
      this.models.keyboardInteractionModel.spaceHeld = false;
    }
  }
}
