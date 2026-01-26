import { CanvasModel } from "../model";
import { IView } from "./base";

type Models = Pick<
  CanvasModel,
  "canvasElementModel" | "transformModel" | "imageBufferModel"
>;

export class ImageLayerView extends IView<Models> {
  constructor(models: CanvasModel) {
    super(models);
  }

  render(): void {
    const { buffer } = this.models.imageBufferModel;
    const { corners } = this.models.transformModel;

    if (!buffer || !corners) return;

    const ctx = this.models.canvasElementModel.ctx;

    ctx.save();

    // Calculate bounding rect from corners
    const minX = Math.min(
      corners.topLeft.x,
      corners.topRight.x,
      corners.bottomRight.x,
      corners.bottomLeft.x
    );
    const minY = Math.min(
      corners.topLeft.y,
      corners.topRight.y,
      corners.bottomRight.y,
      corners.bottomLeft.y
    );
    const maxX = Math.max(
      corners.topLeft.x,
      corners.topRight.x,
      corners.bottomRight.x,
      corners.bottomLeft.x
    );
    const maxY = Math.max(
      corners.topLeft.y,
      corners.topRight.y,
      corners.bottomRight.y,
      corners.bottomLeft.y
    );

    ctx.drawImage(buffer, minX, minY, maxX - minX, maxY - minY);

    ctx.restore();
  }

  clear(): void {
    const { htmlCanvas, ctx } = this.models.canvasElementModel;

    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, htmlCanvas.width, htmlCanvas.height);
    ctx.restore();
  }
}
