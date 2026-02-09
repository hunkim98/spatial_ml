import { IModel } from "../base";

export type ILayerModelType<T> = {
  width: number;
  height: number;
  dpr: number;
  element: HTMLCanvasElement;
} & T;

export abstract class ILayerModel<T> extends IModel<ILayerModelType<T>> {
  private _width: number;
  private _height: number;
  private _dpr: number;
  private _ctx: CanvasRenderingContext2D;
  private _element: HTMLCanvasElement;

  constructor({ width, height, dpr, element }: ILayerModelType<T>) {
    super();
    this._width = width;
    this._height = height;
    this._dpr = dpr;
    this._element = element;
    this._ctx = this.element.getContext("2d")!;
  }

  get width(): number {
    return this._width;
  }
  get height(): number {
    return this._height;
  }
  get dpr(): number {
    return this._dpr;
  }
  get ctx(): CanvasRenderingContext2D {
    return this._ctx;
  }
  get element(): HTMLCanvasElement {
    return this._element;
  }

  set width(width: number) {
    this._width = width;
  }
  set height(height: number) {
    this._height = height;
  }
  set dpr(dpr: number) {
    this._dpr = dpr;
  }
  set ctx(ctx: CanvasRenderingContext2D) {
    this._ctx = ctx;
  }
  set element(element: HTMLCanvasElement) {
    this._element = element;
  }
}
