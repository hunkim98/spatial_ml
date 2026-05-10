import { ILayerModel, ILayerModelType } from "./base";

export type OverlayLayerModelType = {};

export class OverlayLayerModel
  extends ILayerModel<OverlayLayerModelType>
  implements OverlayLayerModelType
{
  constructor(props: ILayerModelType<OverlayLayerModelType>) {
    super(props);
  }

  reset() {
    // Nothing to reset
  }
}
