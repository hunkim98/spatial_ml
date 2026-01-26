import { IModel } from "../model/base";
import { CanvasModel } from "../model";

export abstract class IView<M> {
  models: M;

  constructor(models: CanvasModel) {
    const neededModelKeys = Object.keys(models) as Array<keyof CanvasModel>;

    this.models = neededModelKeys.reduce(
      (modelKeys, key) => {
        modelKeys[key] = models[key] as IModel<M>;
        return modelKeys;
      },
      {} as { [key in keyof CanvasModel]: IModel<M> }
    ) as M;
  }

  abstract render(): void;

  clear() {
    throw new Error("Method not implemented.");
  }
}
