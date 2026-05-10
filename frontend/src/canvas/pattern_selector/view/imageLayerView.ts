import { PatternSelectorModel } from "../model";
import { Point } from "../types";
import { getCanvasRelativePositionFromWorldPoint } from "../utils/project";
import { IView } from "./base";

type Models = Pick<
  PatternSelectorModel,
  "imageLayerModel" | "imageModel" | "navigationModel"
>;

export class ImageLayerView extends IView<Models> {
  constructor(models: PatternSelectorModel) {
    super(models);
  }

  scale(dpr: number) {
    this.models.imageLayerModel.ctx.scale(dpr, dpr);
  }

  render(): void {
    const { ctx } = this.models.imageLayerModel;
    const { image, leftTop, width, height } = this.models.imageModel;
    if (!width || !height || !image) return;

    const { offset, scale } = this.models.navigationModel;

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
      image,
      imageLeftTopCanvasPoint.x,
      imageLeftTopCanvasPoint.y,
      width * scale,
      height * scale
    );
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
