import { IModel } from "./base";
import { ClipRect } from "../types";
import { Action } from "../actions/base";

const MAX_HISTORY_SIZE = 50;

export interface HistoryModelType {
  undoStack: Array<Action>;
  redoStack: Array<Action>;
}

export class HistoryModel extends IModel<HistoryModel> {
  private _undoStack: Array<Action>;
  private _redoStack: Array<Action>;

  constructor(props: Partial<HistoryModelType> = {}) {
    super();
    this._undoStack = props.undoStack ?? [];
    this._redoStack = props.redoStack ?? [];
  }

  get undoStack(): Array<Action> {
    return this._undoStack;
  }
  get redoStack(): Array<Action> {
    return this._redoStack;
  }

  set redoStack(a: Array<Action>) {
    if (a.length > 0) {
      throw new Error("You can only set the redoStack with an empty array");
    }
    this._redoStack = a;
  }
}
