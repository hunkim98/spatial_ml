import { ModeController } from "./modeController";
import { ImageUploadController } from "./imageUploadController";
import { MouseInteractionController } from "./mouseInteractionController";
import { DragInteractionController } from "./dragInteractionController";
import { ToolManagerController } from "./tools/toolManagerController";
import { ImageCreateToolController } from "./tools/imageCreateToolController";
import { ImageMoveToolController } from "./tools/imageMoveToolController";
import { ImageResizeToolController } from "./tools/imageResizeToolController";
import { ImageRotateToolController } from "./tools/imageRotateToolController";
import { PdfUpdateController } from "./input/pdfUpdateController";
import { ImageUpdateController } from "./input/imageUpdateController";
import { BufferUpdateController } from "./input/bufferUpdateController";

export type CanvasController = {
  modeController: ModeController;
  imageUploadController: ImageUploadController;
  mouseInteractionController: MouseInteractionController;
  dragInteractionController: DragInteractionController;
  toolManagerController: ToolManagerController;
  imageCreateToolController: ImageCreateToolController;
  imageMoveToolController: ImageMoveToolController;
  imageResizeToolController: ImageResizeToolController;
  imageRotateToolController: ImageRotateToolController;
  pdfUpdateController: PdfUpdateController;
  imageUpdateController: ImageUpdateController;
  bufferUpdateController: BufferUpdateController;
};
