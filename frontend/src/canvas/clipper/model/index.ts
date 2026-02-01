import { ClipRectToolModel } from "./tools/clipRectToolModel";
import { MaskLayerModel } from "./layers/frameLayerModel";
import { PdfLayerModel } from "./layers/pdfLayerModel";
import { EditorStatusModel } from "./editorStatusModel";
import { HistoryModel } from "./historyModel";
import { ImageModel } from "./imageModel";
import { MouseControlModel } from "./mouseControlModel";
import { NavigationModel } from "./navigationModel";

export type ClipperModel = {
  maskLayerModel: MaskLayerModel;
  pdfLayerModel: PdfLayerModel;
  imageModel: ImageModel;
  clipRectToolModel: ClipRectToolModel;
  editorStatusModel: EditorStatusModel;
  historyModel: HistoryModel;
  mouseControlModel: MouseControlModel;
  navigationModel: NavigationModel;
};
