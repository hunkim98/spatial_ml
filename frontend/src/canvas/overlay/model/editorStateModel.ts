import { IModel } from "./base";

export class EditorStateModel extends IModel<EditorStateModel> {
  isLoaded: boolean = false;
  isInitialized: boolean = false; // True after initial bounds are created

  reset() {
    this.isLoaded = false;
    this.isInitialized = false;
  }
}
