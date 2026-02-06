import { HandleType } from "../../types";
import { ToolType } from "../../types/tool";
import { IModel } from "../base";

interface ToolManagerModelType {
  activeTool: ToolType | null;
}

export class ToolManagerModel
  extends IModel<ToolManagerModelType>
  implements ToolManagerModelType
{
  private _activeTool: ToolType | null;

  constructor(props: Partial<ToolManagerModelType>) {
    super();
    this._activeTool = props.activeTool ?? null;
  }

  get activeTool(): ToolType | null {
    return this._activeTool;
  }

  set activeTool(tool: ToolType | null) {
    this._activeTool = tool;
  }
  reset() {
    this._activeTool = null;
  }
}
