import { ClipperModel } from "../model";
import { IView } from "./base";
import { Point } from "../types/geometry";

const HANDLE_SIZE = 8;
const STROKE_COLOR = "#6D96FF";
const STROKE_WIDTH = 2;

type Models = Pick<ClipperModel, "frameLayerModel" | "clipRectToolModel">;

export class MaskLayerView extends IView<Models> {
  constructor(models: ClipperModel) {
    super(models);
  }

  render(): void {
    const { rect } = this.models.clipRectToolModel;

    if (!rect) return;

    const ctx = this.models.frameLayerModel.ctx;

    ctx.save();

    // Draw mask border
    ctx.strokeStyle = STROKE_COLOR;
    ctx.lineWidth = STROKE_WIDTH;
    ctx.strokeRect(rect.offset.x, rect.offset.y, rect.width, rect.height);

    // Calculate corner positions
    const topLeft: Point = { x: rect.offset.x, y: rect.offset.y };
    const topRight: Point = { x: rect.offset.x + rect.width, y: rect.offset.y };
    const bottomRight: Point = {
      x: rect.offset.x + rect.width,
      y: rect.offset.y + rect.height,
    };
    const bottomLeft: Point = { x: rect.offset.x, y: rect.offset.y + rect.height };

    // Draw corner handles
    this.drawHandle(ctx, topLeft);
    this.drawHandle(ctx, topRight);
    this.drawHandle(ctx, bottomRight);
    this.drawHandle(ctx, bottomLeft);

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
    const { element, ctx } = this.models.frameLayerModel;
    if (!element || !ctx) return;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
