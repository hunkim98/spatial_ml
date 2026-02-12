import { CanvasModel } from "../model";
import { IView } from "./base";
import { getCanvasRelativePositionFromWorldPoint } from "../utils/project";
import { Point } from "../types";

type Models = Pick<
  CanvasModel,
  | "imageLayerModel"
  | "imageTransformToolModel"
  | "imageBufferModel"
  | "navigationModel"
>;

export class ImageLayerView extends IView<Models> {
  constructor(models: CanvasModel) {
    super(models);
  }

  render(): void {
    const { ctx } = this.models.imageLayerModel;
    const { buffer, leftTop, width, height } = this.models.imageBufferModel;
    if (!buffer || !width || !height) return;
    const { offset, scale } = this.models.navigationModel;

    // Convert world position to canvas position
    const imageLeftTopWorldPoint: Point = {
      x: leftTop.x,
      y: leftTop.y,
    };
    const imageLeftTopCanvasPoint: Point =
      getCanvasRelativePositionFromWorldPoint(
        imageLeftTopWorldPoint,
        offset,
        scale
      );

    ctx.save();
    ctx.drawImage(
      buffer,
      imageLeftTopCanvasPoint.x,
      imageLeftTopCanvasPoint.y,
      width * scale,
      height * scale
    );
    ctx.restore();
  }

  scale(dpr: number): void {
    this.models.imageLayerModel.ctx.scale(dpr, dpr);
  }

  clear(): void {
    const { element, ctx } = this.models.imageLayerModel;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
