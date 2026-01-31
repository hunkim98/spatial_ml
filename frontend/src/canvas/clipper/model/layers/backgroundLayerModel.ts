import { ILayerModel, ILayerModelType } from "./base";

export interface BackgroundLayerModelType {
  backgroundColor?: string;
}

export class BackgroundLayerModel
  extends ILayerModel<BackgroundLayerModelType>
  implements BackgroundLayerModelType
{
  private _backgroundColor: string;

  constructor(props: ILayerModelType<BackgroundLayerModelType>) {
    super(props);
    this._backgroundColor = props.backgroundColor ?? "#000000";
  }

  get backgroundColor(): string {
    return this._backgroundColor;
  }

  set backgroundColor(backgroundColor: string) {
    this._backgroundColor = backgroundColor;
  }
}
