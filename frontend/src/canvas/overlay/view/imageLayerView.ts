import { CanvasModel } from "../model";
import { IView } from "./base";

type Models = Pick<
  CanvasModel,
  "imageLayerModel" | "imageTransformToolModel" | "imageBufferModel"
>;

export class ImageLayerView extends IView<Models> {
  constructor(models: CanvasModel) {
    super(models);
  }

  render(): void {
    const { buffer } = this.models.imageBufferModel;
    const { corners } = this.models.imageTransformToolModel;

    if (!buffer || !corners) return;

    const ctx = this.models.imageLayerModel.ctx;

    ctx.save();

    // Calculate bounding rect from corners
    const minX = Math.min(
      corners.corner1.x,
      corners.corner2.x,
      corners.corner3.x,
      corners.corner4.x
    );
    const minY = Math.min(
      corners.corner1.y,
      corners.corner2.y,
      corners.corner3.y,
      corners.corner4.y
    );
    const maxX = Math.max(
      corners.corner1.x,
      corners.corner2.x,
      corners.corner3.x,
      corners.corner4.x
    );
    const maxY = Math.max(
      corners.corner1.y,
      corners.corner2.y,
      corners.corner3.y,
      corners.corner4.y
    );

    ctx.drawImage(buffer, minX, minY, maxX - minX, maxY - minY);

    ctx.restore();
  }

  clear(): void {
    const { element, ctx } = this.models.imageLayerModel;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, element.width, element.height);
    ctx.restore();
  }
}
