import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { BaseController } from "../base";
import { ClipperEventListeners } from "../../events";
import { ToolType } from "../../types/tool";
import { HandleType, Point, Rect } from "../../types";
import {
  isInsideRect,
  isNearPoint,
  getScaledHitRadius,
} from "../../lib/geometry";

type Models = Pick<
  ClipperModel,
  | "toolManagerModel"
  | "clipRectToolModel"
  | "imageModel"
  | "mouseInteractionModel"
  | "navigationModel"
>;
type Views = never;
type ExecuteParams = {
  e: React.WheelEvent<HTMLCanvasElement> | React.MouseEvent<HTMLCanvasElement>;
};

// This tool will control which tool to use based on the interaction with the canvas.
// When the user's mouse is around the borders of the image, it will activate the clip rect edit
export class ToolManagerController extends BaseController<
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
    this.detectTool();
    console.log(
      "active:",
      this.models.toolManagerModel.activeTool,
      this.models.clipRectToolModel.activeHandle,
      "candidate:",
      this.models.toolManagerModel.candidateTool,
      this.models.clipRectToolModel.candidateHandle
    );
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
    const isInsideImage = this.detectInsideImage();

    if (!isInsideImage) {
      this.setCandidate(null, null);
      return;
    }

    const hasRect = !!this.models.clipRectToolModel.rect;
    if (!hasRect) {
      this.setCandidate(ToolType.CLIP_RECT_CREATE, null);
      return;
    }

    const handleAtPoint = this.detectOnClipRect();
    if (handleAtPoint) {
      this.setCandidate(ToolType.CLIP_RECT_RESIZE, handleAtPoint);
    } else {
      this.setCandidate(null, null);
    }
  }

  private shouldLockActiveTool(): boolean {
    return (
      this.models.clipRectToolModel.isCreating ||
      this.models.clipRectToolModel.isEditing
    );
  }

  private setCandidate(tool: ToolType | null, handle: HandleType | null) {
    this.models.toolManagerModel.candidateTool = tool;
    this.models.clipRectToolModel.candidateHandle = handle;
  }

  private applyCandidateToActive() {
    this.models.toolManagerModel.activeTool =
      this.models.toolManagerModel.candidateTool;
    this.models.clipRectToolModel.activeHandle =
      this.models.clipRectToolModel.candidateHandle;
  }

  detectInsideImage() {
    // we would have to use mouse move position
    if (!this.models.mouseInteractionModel.mouseMoveWorldPosition) return false;
    const { width, height, leftTop } = this.models.imageModel;
    if (!width || !height || !leftTop) return false;
    return isInsideRect(
      this.models.mouseInteractionModel.mouseMoveWorldPosition,
      {
        offset: leftTop,
        width,
        height,
      }
    );
  }

  detectOnClipRect() {
    if (!this.models.mouseInteractionModel.mouseMoveWorldPosition) return null;
    const { rect } = this.models.clipRectToolModel;
    if (!rect) return null;

    // Get scale-adjusted hit radius (larger when zoomed out)
    const scale = this.models.navigationModel.scale;
    const hitRadius = getScaledHitRadius(scale);

    const topLeft: Point = { x: rect.offset.x, y: rect.offset.y };
    const topRight: Point = { x: rect.offset.x + rect.width, y: rect.offset.y };
    const bottomRight: Point = {
      x: rect.offset.x + rect.width,
      y: rect.offset.y + rect.height,
    };
    const bottomLeft: Point = {
      x: rect.offset.x,
      y: rect.offset.y + rect.height,
    };
    const left: Point = {
      x: rect.offset.x,
      y: rect.offset.y + rect.height / 2,
    };
    const right: Point = {
      x: rect.offset.x + rect.width,
      y: rect.offset.y + rect.height / 2,
    };
    const top: Point = { x: rect.offset.x + rect.width / 2, y: rect.offset.y };
    const bottom: Point = {
      x: rect.offset.x + rect.width / 2,
      y: rect.offset.y + rect.height,
    };
    const point = this.models.mouseInteractionModel.mouseMoveWorldPosition;

    // Check corner handles first (they have priority)
    if (isNearPoint(point, topLeft, hitRadius)) return HandleType.TOP_LEFT;
    if (isNearPoint(point, topRight, hitRadius)) return HandleType.TOP_RIGHT;
    if (isNearPoint(point, bottomRight, hitRadius))
      return HandleType.BOTTOM_RIGHT;
    if (isNearPoint(point, bottomLeft, hitRadius))
      return HandleType.BOTTOM_LEFT;
    if (isNearPoint(point, left, hitRadius)) return HandleType.LEFT;
    if (isNearPoint(point, right, hitRadius)) return HandleType.RIGHT;
    if (isNearPoint(point, top, hitRadius)) return HandleType.TOP;
    if (isNearPoint(point, bottom, hitRadius)) return HandleType.BOTTOM;
    return null;
  }
}
