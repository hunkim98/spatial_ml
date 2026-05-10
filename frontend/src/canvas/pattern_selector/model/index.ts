import { ImageLayerModel } from "./layers/imageLayerModel";
import { OverlayLayerModel } from "./layers/overlayLayerModel";
import { ImageModel } from "./imageModel";
import { NavigationModel } from "./navigationModel";
import { MouseInteractionModel } from "./mouseInteractionModel";
import { DragInteractionModel } from "./dragInteractionModel";
import { EditorStatusModel } from "./editorStatusModel";
import { PatternCirclesModel } from "./patternCirclesModel";
import { ToolManagerModel } from "./toolManagerModel";

export type PatternSelectorModel = {
  imageLayerModel: ImageLayerModel;
  overlayLayerModel: OverlayLayerModel;
  imageModel: ImageModel;
  navigationModel: NavigationModel;
  mouseInteractionModel: MouseInteractionModel;
  dragInteractionModel: DragInteractionModel;
  editorStatusModel: EditorStatusModel;
  patternCirclesModel: PatternCirclesModel;
  toolManagerModel: ToolManagerModel;
};
