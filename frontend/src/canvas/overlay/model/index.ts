import { MouseInteractionModel } from "./mouseInteractionModel";
import { EditorStateModel } from "./editorStateModel";
import { ImageBufferModel } from "./imageBufferModel";
import { NavigationModel } from "./navigationModel";
import { DragInteractionModel } from "./dragInteractionModel";
import { ToolManagerModel } from "./tools/toolManagerModel";
import { ImageTransformToolModel } from "./tools/imageTransformToolModel";
import { ImageLayerModel } from "./layers/imageLayerModel";
import { FrameLayerModel } from "./layers/frameLayerModel";

export type CanvasModel = {
  imageLayerModel: ImageLayerModel;
  frameLayerModel: FrameLayerModel;
  mouseInteractionModel: MouseInteractionModel;
  editorStateModel: EditorStateModel;
  imageBufferModel: ImageBufferModel;
  navigationModel: NavigationModel;
  dragInteractionModel: DragInteractionModel;
  toolManagerModel: ToolManagerModel;
  imageTransformToolModel: ImageTransformToolModel;
};
