import { PatternSelectorEventListeners } from "../events";
import { PatternSelectorModel } from "../model";
import { PatternToolType } from "../model/toolManagerModel";
import { PatternSelectorView } from "../view";
import { Point } from "../types";
import { distance } from "../utils/math";
import { BaseController } from "./base";

const EDGE_HIT_THRESHOLD = 8; // pixels (in world space) tolerance for edge detection

type Models = Pick<
  PatternSelectorModel,
  | "toolManagerModel"
  | "patternCirclesModel"
  | "mouseInteractionModel"
  | "navigationModel"
>;
type Views = never;

type ExecuteParams = {
  e: React.MouseEvent<HTMLCanvasElement>;
};

/**
 * Detects which tool should be active based on mouse position relative
 * to existing pattern circles.
 *
 * Priority: edge (RESIZE) > body (MOVE) > empty space (CREATE)
 */
export class ToolManagerController extends BaseController<
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

    // Don't update candidate during active interaction
    if (
      e.type !== "mousedown" &&
      this.models.toolManagerModel.activeTool !== null
    ) {
      return;
    }

    const mousePos = this.getCurrentWorldPosition();
    if (!mousePos) {
      this.models.toolManagerModel.candidateTool = PatternToolType.CREATE;
      this.models.toolManagerModel.candidateCircleId = null;
      return;
    }

    const { circles } = this.models.patternCirclesModel;
    const scale = this.models.navigationModel.scale;
    // Convert screen-space threshold to world-space
    const threshold = EDGE_HIT_THRESHOLD / scale;

    // Check circles in reverse order (last drawn = top)
    for (let i = circles.length - 1; i >= 0; i--) {
      const circle = circles[i];
      const dist = distance(mousePos, circle.center);

      // Check edge first (higher priority)
      if (Math.abs(dist - circle.radius) <= threshold) {
        this.models.toolManagerModel.candidateTool = PatternToolType.RESIZE;
        this.models.toolManagerModel.candidateCircleId = circle.id;
        if (e.type === "mousedown") {
          this.models.toolManagerModel.activeTool = PatternToolType.RESIZE;
          this.models.toolManagerModel.activeCircleId = circle.id;
        }
        return;
      }

      // Check body
      if (dist < circle.radius) {
        this.models.toolManagerModel.candidateTool = PatternToolType.MOVE;
        this.models.toolManagerModel.candidateCircleId = circle.id;
        if (e.type === "mousedown") {
          this.models.toolManagerModel.activeTool = PatternToolType.MOVE;
          this.models.toolManagerModel.activeCircleId = circle.id;
        }
        return;
      }
    }

    // Empty space → create
    this.models.toolManagerModel.candidateTool = PatternToolType.CREATE;
    this.models.toolManagerModel.candidateCircleId = null;
    if (e.type === "mousedown") {
      this.models.toolManagerModel.activeTool = PatternToolType.CREATE;
      this.models.toolManagerModel.activeCircleId = null;
    }
  }

  private getCurrentWorldPosition(): Point | null {
    return (
      this.models.mouseInteractionModel.mouseMoveWorldPosition ??
      this.models.mouseInteractionModel.mouseDownWorldPosition
    );
  }
}
