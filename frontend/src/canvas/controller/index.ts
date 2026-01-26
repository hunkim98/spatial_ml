import { HitTestController } from "./hitTestController";
import { ModeController } from "./modeController";
import { ImageCreateController } from "./imageCreateController";
import { ImageMoveController } from "./imageMoveController";
import { ImageResizeController } from "./imageResizeController";
import { ImageRotateController } from "./imageRotateController";

export type CanvasController = {
  hitTestController: HitTestController;
  modeController: ModeController;
  imageCreateController: ImageCreateController;
  imageMoveController: ImageMoveController;
  imageResizeController: ImageResizeController;
  imageRotateController: ImageRotateController;
};
