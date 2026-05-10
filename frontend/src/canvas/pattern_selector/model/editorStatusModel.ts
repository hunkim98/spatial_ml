import { IModel } from "./base";

export interface EditorStatusModelType {
  isLoaded: boolean;
}

export class EditorStatusModel
  extends IModel<EditorStatusModelType>
  implements EditorStatusModelType
{
  private _isLoaded: boolean;

  constructor() {
    super();
    this._isLoaded = false;
  }

  get isLoaded(): boolean {
    return this._isLoaded;
  }
  set isLoaded(value: boolean) {
    this._isLoaded = value;
  }

  reset() {
    this._isLoaded = false;
  }
}
