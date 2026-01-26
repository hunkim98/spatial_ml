import { MouseControlModel } from "./mouseControlModel";
import { EditorStateModel } from "./editorStateModel";
import { TransformModel } from "./transformModel";
import { ImageBufferModel } from "./imageBufferModel";
import { CanvasElementModel } from "./canvasElementModel";

export type CanvasModel = {
  canvasElementModel: CanvasElementModel;
  mouseControlModel: MouseControlModel;
  editorStateModel: EditorStateModel;
  transformModel: TransformModel;
  imageBufferModel: ImageBufferModel;
};
