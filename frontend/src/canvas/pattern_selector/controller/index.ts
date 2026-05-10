import { CanvasSizeController } from "./canvasSizeController";
import { DragInteractionController } from "./dragInteractionController";
import { ImageBufferUpdateController } from "./imageBufferUpdateController";
import { MouseInteractionController } from "./mouseInteractionController";
import { PatternCircleCreateController } from "./patternCircleCreateController";
import { PatternCircleEditController } from "./patternCircleEditController";
import { ToolManagerController } from "./toolManagerController";

export type PatternSelectorController = {
  canvasSizeController: CanvasSizeController;
  imageBufferUpdateController: ImageBufferUpdateController;
  mouseInteractionController: MouseInteractionController;
  dragInteractionController: DragInteractionController;
  toolManagerController: ToolManagerController;
  patternCircleCreateController: PatternCircleCreateController;
  patternCircleEditController: PatternCircleEditController;
};
