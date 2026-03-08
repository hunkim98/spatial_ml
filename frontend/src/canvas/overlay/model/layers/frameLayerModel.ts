import { ILayerModel, ILayerModelType } from "./base";

export interface FrameLayerModelType {}

/**
 * FrameLayerModel - manages the canvas layer for displaying frame and handles
 * Following clipper editor's layer model pattern
 */
export class FrameLayerModel
  extends ILayerModel<FrameLayerModelType>
  implements FrameLayerModelType
{
  constructor(props: ILayerModelType<FrameLayerModelType>) {
    super(props);
  }

  reset() {
    // Nothing to reset for now
  }
}
