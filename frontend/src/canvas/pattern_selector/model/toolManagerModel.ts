import { IModel } from "./base";

export enum PatternToolType {
  CREATE = "CREATE",
  RESIZE = "RESIZE",
  MOVE = "MOVE",
}

export interface ToolManagerModelType {
  activeTool: PatternToolType | null;
  candidateTool: PatternToolType | null;
  activeCircleId: string | null;
  candidateCircleId: string | null;
}

export class ToolManagerModel
  extends IModel<ToolManagerModelType>
  implements ToolManagerModelType
{
  private _activeTool: PatternToolType | null;
  private _candidateTool: PatternToolType | null;
  private _activeCircleId: string | null;
  private _candidateCircleId: string | null;

  constructor() {
    super();
    this._activeTool = null;
    this._candidateTool = null;
    this._activeCircleId = null;
    this._candidateCircleId = null;
  }

  get activeTool(): PatternToolType | null {
    return this._activeTool;
  }
  set activeTool(tool: PatternToolType | null) {
    this._activeTool = tool;
  }

  get candidateTool(): PatternToolType | null {
    return this._candidateTool;
  }
  set candidateTool(tool: PatternToolType | null) {
    this._candidateTool = tool;
  }

  get activeCircleId(): string | null {
    return this._activeCircleId;
  }
  set activeCircleId(id: string | null) {
    this._activeCircleId = id;
  }

  get candidateCircleId(): string | null {
    return this._candidateCircleId;
  }
  set candidateCircleId(id: string | null) {
    this._candidateCircleId = id;
  }

  reset() {
    this._activeTool = null;
    this._candidateTool = null;
    this._activeCircleId = null;
    this._candidateCircleId = null;
  }
}
