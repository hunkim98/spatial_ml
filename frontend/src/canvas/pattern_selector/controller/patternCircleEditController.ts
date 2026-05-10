import { PatternSelectorEventListeners } from "../events";
import { PatternSelectorModel } from "../model";
import { PatternToolType } from "../model/toolManagerModel";
import { PatternSelectorView } from "../view";
import { Point } from "../types";
import { distance } from "../utils/math";
import { BaseController } from "./base";

type Models = Pick<
  PatternSelectorModel,
  "patternCirclesModel" | "mouseInteractionModel" | "toolManagerModel"
>;
type Views = never;

type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

const MIN_RADIUS = 8;

/**
 * Handles resize and move interactions on existing pattern circles.
 *
 * RESIZE: Updates circle radius based on distance from center to mouse.
 * MOVE: Updates circle center based on mouse movement delta.
 */
export class PatternCircleEditController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  private _lastMovePosition: Point | null = null;

  constructor(
    models: PatternSelectorModel,
    views: PatternSelectorView,
    listeners: PatternSelectorEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    const { e } = params;
    const { activeTool, activeCircleId } = this.models.toolManagerModel;

    if (!activeCircleId) return;
    if (activeTool !== PatternToolType.RESIZE && activeTool !== PatternToolType.MOVE) {
      return;
    }

    if (e.type === "mousedown") {
      this._lastMovePosition =
        this.models.mouseInteractionModel.mouseDownWorldPosition;
    } else if (e.type === "mousemove") {
      if (activeTool === PatternToolType.RESIZE) {
        this.executeResize(activeCircleId);
      } else if (activeTool === PatternToolType.MOVE) {
        this.executeMove(activeCircleId);
      }
    } else if (e.type === "mouseup") {
      this._lastMovePosition = null;
      this.models.toolManagerModel.activeTool = null;
      this.models.toolManagerModel.activeCircleId = null;
    }
  }

  private executeResize(circleId: string): void {
    const mousePos =
      this.models.mouseInteractionModel.mouseMoveWorldPosition;
    if (!mousePos) return;

    const circles = this.models.patternCirclesModel.circles;
    const idx = circles.findIndex((c) => c.id === circleId);
    if (idx === -1) return;

    const circle = circles[idx];
    const newRadius = Math.max(MIN_RADIUS, distance(circle.center, mousePos));

    // Update in place
    this.models.patternCirclesModel.circles = circles.map((c, i) =>
      i === idx ? { ...c, radius: newRadius } : c
    );
  }

  private executeMove(circleId: string): void {
    const mousePos =
      this.models.mouseInteractionModel.mouseMoveWorldPosition;
    if (!mousePos || !this._lastMovePosition) return;

    const dx = mousePos.x - this._lastMovePosition.x;
    const dy = mousePos.y - this._lastMovePosition.y;

    const circles = this.models.patternCirclesModel.circles;
    const idx = circles.findIndex((c) => c.id === circleId);
    if (idx === -1) return;

    const circle = circles[idx];
    this.models.patternCirclesModel.circles = circles.map((c, i) =>
      i === idx
        ? {
            ...c,
            center: { x: circle.center.x + dx, y: circle.center.y + dy },
          }
        : c
    );

    this._lastMovePosition = mousePos;
  }
}
