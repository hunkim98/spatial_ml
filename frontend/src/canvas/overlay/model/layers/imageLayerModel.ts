import { ILayerModel, ILayerModelType } from "./base";

export type ImageLayerModelType = {};

/**
 * ImageLayerModel - manages the canvas layer for displaying the image
 * Following clipper editor's layer model pattern
 */
export class ImageLayerModel
  extends ILayerModel<ImageLayerModelType>
  implements ImageLayerModelType
{
  constructor(props: ILayerModelType<ImageLayerModelType>) {
    super(props);
  }

  reset() {
    // Nothing to reset for now
  }
}
