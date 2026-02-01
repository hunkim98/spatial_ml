import { Point } from "../types/geometry";
import { IModel } from "./base";

export interface ImageModelType {
  image: HTMLImageElement | null;
  blob: Blob | null;
  blobUrl: string | null;
  width: number | null;
  height: number | null;
  leftTop: Point;
}

export class ImageModel
  extends IModel<ImageModelType>
  implements ImageModelType
{
  private _image: HTMLImageElement | null;
  private _blob: Blob | null;
  private _blobUrl: string | null;
  private _width: number | null;
  private _height: number | null;
  private _leftTop: Point;

  constructor(props: ImageModelType) {
    super();
    this._image = props.image;
    this._blob = props.blob;
    this._blobUrl = props.blobUrl;
    this._width = props.width;
    this._height = props.height;
    this._leftTop = props.leftTop;
  }

  get image(): HTMLImageElement | null {
    return this._image;
  }

  set image(image: HTMLImageElement | null) {
    this._image = image;
  }

  get blob(): Blob | null {
    return this._blob;
  }

  set blob(blob: Blob | null) {
    this._blob = blob;
  }

  get blobUrl(): string | null {
    return this._blobUrl;
  }

  set blobUrl(url: string | null) {
    // Revoke old URL if exists to prevent memory leak
    if (this._blobUrl) {
      URL.revokeObjectURL(this._blobUrl);
    }
    this._blobUrl = url;
  }

  get width(): number | null {
    return this._width;
  }

  set width(width: number | null) {
    this._width = width;
  }

  get height(): number | null {
    return this._height;
  }

  set height(height: number | null) {
    this._height = height;
  }

  get leftTop(): Point {
    return this._leftTop;
  }

  set leftTop(leftTop: Point) {
    this._leftTop = leftTop;
  }

  reset() {
    if (this._blobUrl) {
      URL.revokeObjectURL(this._blobUrl);
    }
    this._image = null;
    this._blob = null;
    this._blobUrl = null;
    this._width = 0;
    this._height = 0;
    this._leftTop = { x: 0, y: 0 };
  }
}
