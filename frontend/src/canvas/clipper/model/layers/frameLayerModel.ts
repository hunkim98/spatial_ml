import { ILayerModel, ILayerModelType } from "./base";

export interface MaskLayerModelType {}

export class MaskLayerModel
  extends ILayerModel<MaskLayerModelType>
  implements MaskLayerModelType
{
  constructor(props: ILayerModelType<MaskLayerModelType>) {
    super(props);
  }
}
