import { CanvasModel } from "../model";
import { IView } from "./base";
import { Point } from "../types";

const HANDLE_SIZE = 8;
const STROKE_COLOR = "#6D96FF";
const STROKE_WIDTH = 2;

type Models = Pick<CanvasModel, "frameLayerModel" | "imageTransformToolModel">;

export class FrameLayerView extends IView<Models> {
  constructor(models: CanvasModel) {
    super(models);
  }

  render(): void {
    const { corners } = this.models.imageTransformToolModel;

    if (!corners) return;

    const ctx = this.models.frameLayerModel.ctx;

    ctx.save();

    // Draw frame border
    ctx.strokeStyle = STROKE_COLOR;
    ctx.lineWidth = STROKE_WIDTH;
    ctx.beginPath();
    ctx.moveTo(corners.corner1.x, corners.corner1.y);
    ctx.lineTo(corners.corner2.x, corners.corner2.y);
    ctx.lineTo(corners.corner4.x, corners.corner4.y);
    ctx.lineTo(corners.corner3.x, corners.corner3.y);
    ctx.closePath();
    ctx.stroke();

    // Draw corner handles
    this.drawHandle(ctx, corners.corner1);
    this.drawHandle(ctx, corners.corner2);
    this.drawHandle(ctx, corners.corner4);
    this.drawHandle(ctx, corners.corner3);

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

  scale(dpr: number): void {
    this.models.frameLayerModel.ctx.scale(dpr, dpr);
  }

  clear(): void {
    const { element, ctx } = this.models.frameLayerModel;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
