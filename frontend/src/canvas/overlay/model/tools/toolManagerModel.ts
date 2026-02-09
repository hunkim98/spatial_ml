import { IModel } from "../base";

export enum ToolType {
  IMAGE_CREATE = "IMAGE_CREATE",
  IMAGE_MOVE = "IMAGE_MOVE",
  IMAGE_RESIZE = "IMAGE_RESIZE",
  IMAGE_ROTATE = "IMAGE_ROTATE",
}

interface ToolManagerModelType {
  activeTool: ToolType | null;
  candidateTool: ToolType | null;
}

/**
 * ToolManagerModel - manages active and candidate tools
 * Following clipper editor pattern
 */
export class ToolManagerModel
  extends IModel<ToolManagerModelType>
  implements ToolManagerModelType
{
  private _activeTool: ToolType | null;
  private _candidateTool: ToolType | null;

  constructor(props: Partial<ToolManagerModelType>) {
    super();
    this._activeTool = props.activeTool ?? null;
    this._candidateTool = props.candidateTool ?? null;
  }

  get activeTool(): ToolType | null {
    return this._activeTool;
  }

  set activeTool(tool: ToolType | null) {
    this._activeTool = tool;
  }

  get candidateTool(): ToolType | null {
    return this._candidateTool;
  }

  set candidateTool(tool: ToolType | null) {
    this._candidateTool = tool;
  }

  reset() {
    this._activeTool = null;
    this._candidateTool = null;
  }
}
