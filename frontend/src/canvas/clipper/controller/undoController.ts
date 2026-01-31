import { BaseController } from "./base";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { ClipperEvent, ClipperEventListeners } from "../events";

type Models = Pick<
  ClipperModel,
  "clipRectToolModel" | "historyModel" | "editorStatusModel"
>;
type Views = Pick<ClipperView, never>;

export class UndoController extends BaseController<Models, Views, void> {
  constructor(
    models: ClipperModel,
    views: ClipperView,
    listeners: ClipperEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(): boolean {
    return false;
  }
}
