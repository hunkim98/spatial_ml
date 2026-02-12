import { ModeController } from "./modeController";
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
import { CanvasSizeScaleController } from "./settings/canvasSizeScaleController";
import { ImagePropertyController } from "./imagePropertyController";

export type CanvasController = {
  modeController: ModeController;
  imageUpdateController: ImageUpdateController;
  mouseInteractionController: MouseInteractionController;
  dragInteractionController: DragInteractionController;
  toolManagerController: ToolManagerController;
  imageCreateToolController: ImageCreateToolController;
  imageMoveToolController: ImageMoveToolController;
  imageResizeToolController: ImageResizeToolController;
  imageRotateToolController: ImageRotateToolController;
  pdfUpdateController: PdfUpdateController;
  bufferUpdateController: BufferUpdateController;
  canvasSizeScaleController: CanvasSizeScaleController;
  imagePropertyController: ImagePropertyController;
};
