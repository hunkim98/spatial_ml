import { CanvasEventListeners } from "../events";
import { CanvasModel } from "../model";
import { ScreenCorners } from "../types";
import { CanvasView } from "../view";
import { BaseController } from "./base";

type Models = Pick<
  CanvasModel,
  | "transformSessionModel"
  | "navigationModel"
  | "imageTransformToolModel"
  | "imageBufferModel"
  | "imageLayerModel"
>;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;
type ExecuteParams =
  | { action: "begin"; screenCorners: ScreenCorners }
  | { action: "end" };

/**
 * TransformSessionController — manages the lifecycle of an image transform
 * session. On "begin", saves navigation, sets identity transform so
 * world = screen, sets up corners, and shows the canvas. On "end",
 * clears transform state, restores navigation, and hides the canvas.
 */
export class TransformSessionController extends BaseController<
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
    if (params.action === "begin") {
      this.begin(params.screenCorners);
    } else {
      this.end();
    }
  }

  private begin(screenCorners: ScreenCorners): void {
    const session = this.models.transformSessionModel;
    const nav = this.models.navigationModel;

    // Save current navigation
    session.savedScale = nav.scale;
    session.savedOffset = { ...nav.offset };
    session.isActive = true;

    // Set navigation to identity so world coords = screen coords
    nav.update({ offset: { x: 0, y: 0 }, scale: 1 });

    // Set transform corners (screen coords)
    this.models.imageTransformToolModel.corners = screenCorners;

    // Temporarily show canvas (CSS only — model opacity unchanged)
    this.models.imageLayerModel.element.style.opacity = "1";

    // Render
    this.views.imageLayerView.clear();
    this.views.imageLayerView.render();
    this.views.frameLayerView.clear();
    this.views.frameLayerView.render();
  }

  private end(): void {
    const session = this.models.transformSessionModel;
    const nav = this.models.navigationModel;

    // Clear transform state
    this.models.imageTransformToolModel.corners = null;
    this.models.imageTransformToolModel.isEditing = false;
    this.models.imageTransformToolModel.initialCorners = null;
    this.models.imageTransformToolModel.activeHandle = null;
    this.models.imageTransformToolModel.candidateHandle = null;

    // Restore navigation
    if (session.savedOffset !== null && session.savedScale !== null) {
      nav.update({ offset: session.savedOffset, scale: session.savedScale });
    }
    session.reset();

    // Hide canvas (image goes back to map layer)
    this.models.imageLayerModel.element.style.opacity = "0";

    // Clear render
    this.views.imageLayerView.clear();
    this.views.frameLayerView.clear();
  }
}
