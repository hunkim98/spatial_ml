import { CanvasModel } from "../../model";
import { CanvasView } from "../../view";
import { BaseController } from "../base";
import { CanvasEventListeners } from "../../events";
import { ToolType } from "../../model/tools/toolManagerModel";
import { HandleType, Point } from "../../types";

type Models = Pick<
  CanvasModel,
  | "toolManagerModel"
  | "imageTransformToolModel"
  | "mouseInteractionModel"
  | "editorStateModel"
>;
type Views = never;
type ExecuteParams = {
  e: React.MouseEvent<Element>;
};

const HANDLE_HIT_RADIUS = 12;

/**
 * ToolManagerController - manages tool detection and switching
 * Integrates hit testing similar to clipper editor
 */
export class ToolManagerController extends BaseController<
  Models,
  Views,
  ExecuteParams
> {
  private altHeld = false;

  constructor(
    models: CanvasModel,
    views: CanvasView,
    listeners: CanvasEventListeners
  ) {
    super(models, views, listeners);
  }

  execute(params: ExecuteParams): void {
    this.altHeld = params.e.altKey;
    this.detectTool();
  }

  detectTool() {
    // Always update candidate for cursor display
    this.updateCandidate();

    // Only update active when not in the middle of an interaction
    if (this.shouldLockActiveTool()) {
      return;
    }

    this.applyCandidateToActive();
  }

  private updateCandidate() {
    if (!this.models.editorStateModel.isLoaded) {
      this.setCandidate(null);
      return;
    }

    const forced = this.models.toolManagerModel.forcedTool;

    // Forced IMAGE_CREATE overrides everything (existing behavior)
    if (forced === ToolType.IMAGE_CREATE) {
      this.setCandidate(forced);
      return;
    }

    let handle = this.detectHandle();

    // Alt + body OR forced resize + body = custom anchor resize
    if (
      handle === HandleType.BODY &&
      (this.altHeld || forced === ToolType.IMAGE_RESIZE)
    ) {
      handle = HandleType.CUSTOM_ANCHOR;
    }

    // Forced move: override any handle to BODY (always pan)
    if (forced === ToolType.IMAGE_MOVE && handle !== HandleType.NONE) {
      handle = HandleType.BODY;
    }

    this.models.imageTransformToolModel.candidateHandle =
      handle === HandleType.NONE ? null : handle;

    // Check what handle we're near
    if (handle !== HandleType.NONE) {
      if (handle === HandleType.BODY) {
        this.setCandidate(ToolType.IMAGE_MOVE);
      } else {
        this.setCandidate(ToolType.IMAGE_RESIZE);
      }
    } else {
      this.setCandidate(null);
    }
  }

  private shouldLockActiveTool(): boolean {
    // Lock tool during mouse interaction or when creating/editing image
    return (
      this.models.imageTransformToolModel.isCreating ||
      this.models.imageTransformToolModel.isEditing
    );
  }

  private setCandidate(tool: ToolType | null) {
    this.models.toolManagerModel.candidateTool = tool;
  }

  private applyCandidateToActive() {
    this.models.toolManagerModel.activeTool =
      this.models.toolManagerModel.candidateTool;
    this.models.imageTransformToolModel.activeHandle =
      this.models.imageTransformToolModel.candidateHandle;
  }

  /**
   * Detect which handle (if any) is at the current mouse position
   * Reads position from mouseInteractionModel.mouseMoveWorldPosition
   */
  detectHandle(): HandleType {
    const point = this.getCurrentMousePosition();
    if (!point) return HandleType.NONE;

    const { corners } = this.models.imageTransformToolModel;
    if (!corners) return HandleType.NONE;

    // Check corner handles first (they have priority)
    if (this.isNearPoint(point, corners.corner1)) return HandleType.TOP_LEFT;
    if (this.isNearPoint(point, corners.corner2)) return HandleType.TOP_RIGHT;
    if (this.isNearPoint(point, corners.corner4))
      return HandleType.BOTTOM_RIGHT;
    if (this.isNearPoint(point, corners.corner3)) return HandleType.BOTTOM_LEFT;

    // Check edge handles (entire edge, not just midpoint)
    if (this.isNearEdge(point, corners.corner1, corners.corner2))
      return HandleType.TOP_EDGE;
    if (this.isNearEdge(point, corners.corner2, corners.corner4))
      return HandleType.RIGHT_EDGE;
    if (this.isNearEdge(point, corners.corner3, corners.corner4))
      return HandleType.BOTTOM_EDGE;
    if (this.isNearEdge(point, corners.corner1, corners.corner3))
      return HandleType.LEFT_EDGE;

    // Check if inside the polygon (body)
    if (this.isInsidePolygon(point, corners)) return HandleType.BODY;

    return HandleType.NONE;
  }

  private getCurrentMousePosition(): Point | null {
    return this.models.mouseInteractionModel.mouseMoveWorldPosition;
  }

  private isNearPoint(p1: Point, p2: Point): boolean {
    const dx = p1.x - p2.x;
    const dy = p1.y - p2.y;
    return Math.sqrt(dx * dx + dy * dy) <= HANDLE_HIT_RADIUS;
  }

  /** Check if point is within HANDLE_HIT_RADIUS of the line segment a→b */
  private isNearEdge(point: Point, a: Point, b: Point): boolean {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return this.isNearPoint(point, a);

    // Project point onto line, clamped to [0,1]
    let t = ((point.x - a.x) * dx + (point.y - a.y) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));

    const closest: Point = { x: a.x + t * dx, y: a.y + t * dy };
    return this.isNearPoint(point, closest);
  }

  private isInsidePolygon(
    point: Point,
    corners: {
      corner1: Point;
      corner2: Point;
      corner3: Point;
      corner4: Point;
    }
  ): boolean {
    const polygon = [
      corners.corner1,
      corners.corner2,
      corners.corner4,
      corners.corner3,
    ];

    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].x;
      const yi = polygon[i].y;
      const xj = polygon[j].x;
      const yj = polygon[j].y;

      const intersect =
        yi > point.y !== yj > point.y &&
        point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi;
      if (intersect) inside = !inside;
    }

    return inside;
  }
}
