import { MouseInteractionController } from "./mouseInteractionController";
import { UndoController } from "./undoController";
import { RedoController } from "./redoController";
import { PdfUpdateController } from "./pdfUpdateController";
import { CanvasSizeScaleController } from "./settings/CanvasSizeScaleController";
import { ToolManagerController } from "./tools/toolManagerController";
import { ClipRectCreateToolController } from "./tools/clipRectCreateToolController";
import { ClipRectEditToolController } from "./tools/clipRectEditToolController";
import { DragInteractionController } from "./dragInteractionController";
import { ExportController } from "./exportController";

export type ClipperController = {
  dragInteractionController: DragInteractionController;
  mouseInteractionController: MouseInteractionController;
  pdfUpdateController: PdfUpdateController;
  undoController: UndoController;
  redoController: RedoController;
  canvasSizeScaleController: CanvasSizeScaleController;
  toolManagerController: ToolManagerController;
  clipRectCreateToolController: ClipRectCreateToolController;
  clipRectEditToolController: ClipRectEditToolController;
  exportController: ExportController;
};
