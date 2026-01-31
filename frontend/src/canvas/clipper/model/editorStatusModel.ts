import { ActionType } from "../actions/base";
import { IModel } from "./base";

interface EditorStatusModelType {
  isLoading: boolean;
  isLoaded: boolean;
  isInitialized: boolean;
  tool: ActionType;
}

export class EditorStatusModel
  extends IModel<EditorStatusModelType>
  implements EditorStatusModelType
{
  private _isLoading: boolean;
  private _isLoaded: boolean;
  private _isInitialized: boolean;
  private _tool: ActionType;

  constructor(props: Partial<EditorStatusModelType>) {
    super();
    this._isLoading = props.isLoading ?? false;
    this._isLoaded = props.isLoaded ?? false;
    this._isInitialized = props.isInitialized ?? false;
    this._tool = props.tool ?? ActionType.NONE;
  }

  get isLoading(): boolean {
    return this._isLoading;
  }
  get isLoaded(): boolean {
    return this._isLoaded;
  }
  get isInitialized(): boolean {
    return this._isInitialized;
  }
  get tool(): ActionType {
    return this._tool;
  }

  set isLoading(isLoading: boolean) {
    this._isLoading = isLoading;
  }
  set isLoaded(isLoaded: boolean) {
    this._isLoaded = isLoaded;
  }
  set isInitialized(isInitialized: boolean) {
    this._isInitialized = isInitialized;
  }
  set tool(tool: ActionType) {
    this._tool = tool;
  }
}
