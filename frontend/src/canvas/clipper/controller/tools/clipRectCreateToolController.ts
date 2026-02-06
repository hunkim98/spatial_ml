import { BaseController } from "../base";
import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { ClipperEventListeners } from "../../events";

type Models = Pick<ClipperModel, "clipRectToolModel" | "dragInteractionModel">;
type Views = never;
type ExecuteParams = {};

export class ClipRectCreateToolController extends BaseController<
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
  execute(e: ExecuteParams): void {}
}
