import { BaseController } from "./base";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { CanvasEvent, CanvasEventListeners } from "../events";
import { EditorMode } from "../types";

type Models = Pick<CanvasModel, "editorStateModel">;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

export class ModeController extends BaseController<Models, Views, EditorMode> {
  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(mode: EditorMode): void {
    this.models.editorStateModel.mode = mode;
    this.dispatchEvent(CanvasEvent.MODE_CHANGED);
  }
}
