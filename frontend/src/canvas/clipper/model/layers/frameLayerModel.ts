import { ILayerModel, ILayerModelType } from "./base";

export interface FrameLayerModelType {}

export class FrameLayerModel
  extends ILayerModel<FrameLayerModelType>
  implements FrameLayerModelType
{
  constructor(props: ILayerModelType<FrameLayerModelType>) {
    super(props);
  }
}
