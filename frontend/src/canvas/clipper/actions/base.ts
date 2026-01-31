export enum ActionType {
  MOVE = "move",
  RESIZE = "resize",
  NONE = "none",
}

export abstract class Action {
  abstract _type: ActionType;

  abstract createInverseAction(): Action;

  get type(): ActionType {
    return this._type;
  }
}
