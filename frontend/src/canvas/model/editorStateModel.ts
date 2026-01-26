import { IModel } from "./base";
import { EditorMode } from "../types";

export class EditorStateModel extends IModel<EditorStateModel> {
  mode: EditorMode = EditorMode.CREATE;
  isLoaded: boolean = false;
  isInitialized: boolean = false; // True after initial bounds are created

  reset() {
    this.mode = EditorMode.CREATE;
    this.isLoaded = false;
    this.isInitialized = false;
  }
}
