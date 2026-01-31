import { ClipperModel } from "../model";
import { Point } from "../types/geometry";
import { getCanvasRelativePositionFromWorldPoint } from "../utils/event";
import { IView } from "./base";

type Models = Pick<ClipperModel, "pdfLayerModel" | "imageModel" | "navigationModel">;

export class PdfLayerView extends IView<Models> {
  constructor(models: ClipperModel) {
    super(models);
  }

  render(): void {
    const { ctx } = this.models.pdfLayerModel;
    const { image, leftTop, width, height } = this.models.imageModel;
    const { offset, scale } = this.models.navigationModel;

    if (!image) return;

    // Convert world position to canvas position
    const imageLeftTopWorldPoint: Point = {
      x: leftTop.x,
      y: leftTop.y,
    };
    const imageLeftTopCanvasPoint: Point = getCanvasRelativePositionFromWorldPoint(
      imageLeftTopWorldPoint,
      offset,
      scale
    );

    ctx.save();
    ctx.drawImage(
      image,
      imageLeftTopCanvasPoint.x,
      imageLeftTopCanvasPoint.y,
      width * scale,
      height * scale
    );
    ctx.restore();
  }

  clear(): void {
    const { element, ctx } = this.models.pdfLayerModel;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
