import { MouseInteractionController } from "./mouseInteractionController";
import { UndoController } from "./undoController";
import { RedoController } from "./redoController";
import { PdfUpdateController } from "./pdfUpdateController";
import { CanvasSizeScaleController } from "./settings/CanvasSizeScaleController";
import { ToolManagerController } from "./tools/toolManagerController";
import { ClipRectCreateToolController } from "./tools/clipRectCreateToolController";
import { DragInteractionController } from "./dragInteractionController";

export type ClipperController = {
  dragInteractionController: DragInteractionController;
  mouseInteractionController: MouseInteractionController;
  pdfUpdateController: PdfUpdateController;
  undoController: UndoController;
  redoController: RedoController;
  canvasSizeScaleController: CanvasSizeScaleController;
  toolManagerController: ToolManagerController;
  clipRectCreateToolController: ClipRectCreateToolController;
};
