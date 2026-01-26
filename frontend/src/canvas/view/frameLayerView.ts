import { CanvasModel } from "../model";
import { IView } from "./base";
import { Point } from "../types";

const HANDLE_SIZE = 8;
const STROKE_COLOR = "#6D96FF";
const STROKE_WIDTH = 2;

type Models = Pick<CanvasModel, "canvasElementModel" | "transformModel">;

export class FrameLayerView extends IView<Models> {
  constructor(models: CanvasModel) {
    super(models);
  }

  render(): void {
    const { corners } = this.models.transformModel;

    if (!corners) return;

    const ctx = this.models.canvasElementModel.ctx;

    ctx.save();

    // Draw frame border
    ctx.strokeStyle = STROKE_COLOR;
    ctx.lineWidth = STROKE_WIDTH;
    ctx.beginPath();
    ctx.moveTo(corners.topLeft.x, corners.topLeft.y);
    ctx.lineTo(corners.topRight.x, corners.topRight.y);
    ctx.lineTo(corners.bottomRight.x, corners.bottomRight.y);
    ctx.lineTo(corners.bottomLeft.x, corners.bottomLeft.y);
    ctx.closePath();
    ctx.stroke();

    // Draw corner handles
    this.drawHandle(ctx, corners.topLeft);
    this.drawHandle(ctx, corners.topRight);
    this.drawHandle(ctx, corners.bottomRight);
    this.drawHandle(ctx, corners.bottomLeft);

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
    const { htmlCanvas, ctx } = this.models.canvasElementModel;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, htmlCanvas.width, htmlCanvas.height);
    ctx.restore();
  }
}
