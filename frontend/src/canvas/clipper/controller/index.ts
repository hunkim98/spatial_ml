import { HitTestController } from "./hitTestController";

import { MouseInteractionController } from "./mouseInteractionController";
import { ResizeController } from "./resizeController";
import { UndoController } from "./undoController";
import { RedoController } from "./redoController";
import { PdfUpdateController } from "./pdfUpdateController";
import { CanvasSizeScaleController } from "./settings/CanvasSizeScaleController";

export type ClipperController = {
  mouseInteractionController: MouseInteractionController;
  hitTestController: HitTestController;
  pdfUpdateController: PdfUpdateController;
  resizeController: ResizeController;
  undoController: UndoController;
  redoController: RedoController;
  canvasSizeScaleController: CanvasSizeScaleController;
};
