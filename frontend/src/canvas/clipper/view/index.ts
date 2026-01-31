import { PdfLayerView } from "./pdfLayerView";
import { MaskLayerView } from "./maskLayerView";

export type ClipperView = {
  pdfLayerView: PdfLayerView;
  maskLayerView: MaskLayerView;
};
