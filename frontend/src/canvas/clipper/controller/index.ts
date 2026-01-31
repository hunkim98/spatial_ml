import { HitTestController } from "./hitTestController";
import { ImageUpdateController } from "./imageUpdateController";
import { MoveController } from "./moveController";
import { PanZoomController } from "./panZoomController";
import { ResizeController } from "./resizeController";
import { UndoController } from "./undoController";
import { RedoController } from "./redoController";

export type ClipperController = {
  hitTestController: HitTestController;
  imageUpdateController: ImageUpdateController;
  moveController: MoveController;
  panZoomController: PanZoomController;
  resizeController: ResizeController;
  undoController: UndoController;
  redoController: RedoController;
};
