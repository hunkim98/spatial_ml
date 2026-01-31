import { BaseController } from "./base";
import { ClipperModel } from "../model";
import { ClipperView } from "../view";
import { ClipperEventListeners } from "../events";
import { ClipRect, HandleType } from "../types/clipRect";
import { Point } from "../types/geometry";
import { HitTestService } from "../lib/hitTestService";

type Models = Pick<ClipperModel, "clipRectToolModel" | "mouseControlModel">;
type Views = Pick<ClipperView, never>;

type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

export class InteractionController extends BaseController<
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
    switch (params.e.type) {
    }
  }

  onMouseDownExecute(params: ExecuteParams): void {
    const mouseDownPosition = this.models.mouseControlModel.mouseDownPosition;
    if (!mouseDownPosition) return;
    if (!this.models.clipRectToolModel.rect) return;

    const handle = HitTestService.detectHandleType(
      mouseDownPosition,
      this.models.clipRectToolModel.rect
    );
    if (handle === HandleType.NONE) return;
  }
}
