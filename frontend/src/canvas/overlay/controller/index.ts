import { ModeController } from "./modeController";
import { ImageUploadController } from "./imageUploadController";
import { ToolManagerController } from "./tools/toolManagerController";
import { ImageCreateToolController } from "./tools/imageCreateToolController";
import { ImageMoveToolController } from "./tools/imageMoveToolController";
import { ImageResizeToolController } from "./tools/imageResizeToolController";
import { ImageRotateToolController } from "./tools/imageRotateToolController";

export type CanvasController = {
  modeController: ModeController;
  imageUploadController: ImageUploadController;
  toolManagerController: ToolManagerController;
  imageCreateToolController: ImageCreateToolController;
  imageMoveToolController: ImageMoveToolController;
  imageResizeToolController: ImageResizeToolController;
  imageRotateToolController: ImageRotateToolController;
};
