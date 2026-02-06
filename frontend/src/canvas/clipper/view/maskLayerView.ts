import { ClipperModel } from "../model";
import { IView } from "./base";
import { Point } from "../types/geometry";
import { getCanvasRelativePositionFromWorldPoint } from "../utils/project";

const HANDLE_SIZE = 8;
const STROKE_COLOR = "#6D96FF";
const STROKE_WIDTH = 2;
const MASK_FILL = "rgba(0, 0, 0, 0.4)";

type Models = Pick<
  ClipperModel,
  "maskLayerModel" | "clipRectToolModel" | "navigationModel"
>;

export class MaskLayerView extends IView<Models> {
  constructor(models: ClipperModel) {
    super(models);
  }

  scale(dpr: number) {
    this.models.maskLayerModel.ctx.scale(dpr, dpr);
  }

  render(): void {
    this.clear();

    const { corner1, corner2, corner3, corner4 } =
      this.models.clipRectToolModel;

    if (!corner1 || !corner2 || !corner3 || !corner4) return;

    // Compute bounding rect in world space
    const left = Math.min(corner1.x, corner2.x, corner3.x, corner4.x);
    const right = Math.max(corner1.x, corner2.x, corner3.x, corner4.x);
    const top = Math.min(corner1.y, corner2.y, corner3.y, corner4.y);
    const bottom = Math.max(corner1.y, corner2.y, corner3.y, corner4.y);

    const ctx = this.models.maskLayerModel.ctx;
    const { offset, scale } = this.models.navigationModel;
    const { width: canvasWidth, height: canvasHeight } =
      this.models.maskLayerModel;

    // Convert world-space corners to screen-space
    const topLeftScreen = getCanvasRelativePositionFromWorldPoint(
      { x: left, y: top },
      offset,
      scale
    );
    const screenWidth = (right - left) * scale;
    const screenHeight = (bottom - top) * scale;

    ctx.save();

    // Draw semi-transparent mask over the entire canvas with the clip rect cut out
    ctx.fillStyle = MASK_FILL;
    ctx.beginPath();
    ctx.rect(0, 0, canvasWidth, canvasHeight);
    ctx.rect(
      topLeftScreen.x,
      topLeftScreen.y + screenHeight,
      screenWidth,
      -screenHeight
    );
    ctx.fill("evenodd");

    // Draw clip rect border
    ctx.strokeStyle = STROKE_COLOR;
    ctx.lineWidth = STROKE_WIDTH;
    ctx.strokeRect(
      topLeftScreen.x,
      topLeftScreen.y,
      screenWidth,
      screenHeight
    );

    // Screen-space corner positions for handles
    const tlHandle: Point = { x: topLeftScreen.x, y: topLeftScreen.y };
    const trHandle: Point = {
      x: topLeftScreen.x + screenWidth,
      y: topLeftScreen.y,
    };
    const brHandle: Point = {
      x: topLeftScreen.x + screenWidth,
      y: topLeftScreen.y + screenHeight,
    };
    const blHandle: Point = {
      x: topLeftScreen.x,
      y: topLeftScreen.y + screenHeight,
    };

    // Draw corner handles
    this.drawHandle(ctx, tlHandle);
    this.drawHandle(ctx, trHandle);
    this.drawHandle(ctx, brHandle);
    this.drawHandle(ctx, blHandle);

    ctx.restore();
  }

  private drawHandle(ctx: CanvasRenderingContext2D, point: Point): void {
    ctx.fillStyle = "#FFFFFF";
    ctx.strokeStyle = STROKE_COLOR;
    ctx.lineWidth = STROKE_WIDTH;

    ctx.beginPath();
    ctx.rect(
      point.x - HANDLE_SIZE / 2,
      point.y - HANDLE_SIZE / 2,
      HANDLE_SIZE,
      HANDLE_SIZE
    );
    ctx.fill();
    ctx.stroke();
  }

  clear(): void {
    const { element, ctx } = this.models.maskLayerModel;
    if (!element || !ctx) return;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
