import { CanvasEventListeners } from "../events";
import { CanvasModel } from "../model";
import { CanvasView } from "../view";
import { BaseController } from "./base";

type Models = Pick<
  CanvasModel,
  "frameLayerModel" | "navigationModel" | "mouseInteractionModel"
>;
type Views = Pick<CanvasView, "imageLayerView" | "frameLayerView">;

type ExecuteParams = {
  e: React.WheelEvent<HTMLCanvasElement> | React.MouseEvent<Element>;
};

export class MouseInteractionController extends BaseController<
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

    if (e.type === "wheel") {
      this.executeWheel(e as React.WheelEvent<HTMLCanvasElement>);
    } else if (e.type === "mousedown") {
      this.executeMouseDown(e as React.MouseEvent<Element>);
    } else if (e.type === "mousemove") {
      this.executeMouseMove(e as React.MouseEvent<Element>);
    } else if (e.type === "mouseup") {
      this.executeMouseUp(e as React.MouseEvent<Element>);
    }
  }

  private executeWheel(e: React.WheelEvent<HTMLCanvasElement>): void {
    // Wheel interactions handled separately if needed
    // For now, keeping it empty as overlay editor doesn't handle zoom/pan
  }

  private executeMouseDown(e: React.MouseEvent<Element>): void {
    // Mouse positions are already updated in editor.onMouseDown
    // This is kept for consistency with clipper pattern
  }

  private executeMouseMove(e: React.MouseEvent<Element>): void {
    // Mouse move tracking handled by editor
    // This is kept for consistency with clipper pattern
  }

  private executeMouseUp(e: React.MouseEvent<Element>): void {
    // Clear mouse positions on mouse up
  }
}
