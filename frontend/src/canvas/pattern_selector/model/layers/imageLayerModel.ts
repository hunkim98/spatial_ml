import { ILayerModel, ILayerModelType } from "./base";

export type ImageLayerModelType = {};

export class ImageLayerModel
  extends ILayerModel<ImageLayerModelType>
  implements ImageLayerModelType
{
  constructor(props: ILayerModelType<ImageLayerModelType>) {
    super(props);
  }

  reset() {
    // Nothing to reset
  }
}
