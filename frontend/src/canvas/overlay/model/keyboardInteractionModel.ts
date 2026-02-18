import { IModel } from "./base";

export class KeyboardInteractionModel extends IModel<KeyboardInteractionModel> {
  private _spaceHeld: boolean = false;

  get spaceHeld(): boolean {
    return this._spaceHeld;
  }

  set spaceHeld(value: boolean) {
    this._spaceHeld = value;
  }

  reset() {
    this._spaceHeld = false;
  }
}
