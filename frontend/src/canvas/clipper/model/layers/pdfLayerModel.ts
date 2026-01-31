import { ILayerModel, ILayerModelType } from "./base";

export type PdfLayerModelType = {};

export class PdfLayerModel
  extends ILayerModel<PdfLayerModelType>
  implements PdfLayerModelType
{
  constructor(props: ILayerModelType<PdfLayerModelType>) {
    super(props);
  }

  reset() {
    // Nothing to reset for now
  }
}
