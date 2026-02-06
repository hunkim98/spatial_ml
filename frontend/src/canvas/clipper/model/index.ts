import { ClipRectToolModel } from "./tools/clipRectToolModel";
import { MaskLayerModel } from "./layers/frameLayerModel";
import { PdfLayerModel } from "./layers/pdfLayerModel";
import { EditorStatusModel } from "./editorStatusModel";
import { HistoryModel } from "./historyModel";
import { ImageModel } from "./imageModel";
import { MouseInteractionModel } from "./mouseInteractionModel";
import { NavigationModel } from "./navigationModel";
import { ToolManagerModel } from "./tools/toolManagerModel";
import { DragInteractionModel } from "./dragInteractionModel";

export type ClipperModel = {
  maskLayerModel: MaskLayerModel;
  pdfLayerModel: PdfLayerModel;
  imageModel: ImageModel;
  clipRectToolModel: ClipRectToolModel;
  editorStatusModel: EditorStatusModel;
  historyModel: HistoryModel;
  mouseInteractionModel: MouseInteractionModel;
  navigationModel: NavigationModel;
  toolManagerModel: ToolManagerModel;
  dragInteractionModel: DragInteractionModel;
};
