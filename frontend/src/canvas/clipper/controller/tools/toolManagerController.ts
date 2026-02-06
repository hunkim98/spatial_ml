import { ClipperModel } from "../../model";
import { ClipperView } from "../../view";
import { BaseController } from "../base";
import { ClipperEventListeners } from "../../events";
import { ToolType } from "../../types/tool";
import { HandleType, Point, Rect } from "../../types";
import { isInsideRect, isNearPoint } from "../../lib/geometry";
``;
type Models = Pick<
  ClipperModel,
  | "toolManagerModel"
  | "clipRectToolModel"
  | "imageModel"
  | "mouseInteractionModel"
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
      this.models.toolManagerModel.activeTool,
      this.models.clipRectToolModel.activeHandle
    );
  }

  detectTool() {
    const isInsideImage = this.detectInsideImage();
    if (!isInsideImage) {
      this.setTool(null);
      return;
    }
    if (!this.models.clipRectToolModel.rect) {
      this.setTool(ToolType.CLIP_RECT_CREATE);
    }
    const onClipRect = this.detectOnClipRect();
    if (onClipRect) {
      this.models.clipRectToolModel.activeHandle = onClipRect;
      this.setTool(ToolType.CLIP_RECT_RESIZE);
    }
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
    if (isNearPoint(point, topLeft)) return HandleType.TOP_LEFT;
    if (isNearPoint(point, topRight)) return HandleType.TOP_RIGHT;
    if (isNearPoint(point, bottomRight)) return HandleType.BOTTOM_RIGHT;
    if (isNearPoint(point, bottomLeft)) return HandleType.BOTTOM_LEFT;
    if (isNearPoint(point, left)) return HandleType.LEFT;
    if (isNearPoint(point, right)) return HandleType.RIGHT;
    if (isNearPoint(point, top)) return HandleType.TOP;
    if (isNearPoint(point, bottom)) return HandleType.BOTTOM;
    return null;
  }

  setTool(tool: ToolType | null) {
    this.models.toolManagerModel.activeTool = tool;
  }
}
