import { IModel } from "./base";
import { EditorMode } from "../types";

export class EditorStateModel extends IModel<EditorStateModel> {
  isLoaded: boolean = false;
  isInitialized: boolean = false; // True after initial bounds are created
  mode: EditorMode = EditorMode.VIEW;

  reset() {
    this.isLoaded = false;
    this.isInitialized = false;
  }
}
