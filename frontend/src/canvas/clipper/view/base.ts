import { IModel } from "../model/base";
import { ClipperModel } from "../model";

export abstract class IView<M> {
  models: M;

  constructor(models: ClipperModel) {
    const neededModelKeys = Object.keys(models) as Array<keyof ClipperModel>;

    this.models = neededModelKeys.reduce(
      (modelKeys, key) => {
        modelKeys[key] = models[key] as IModel<M>;
        return modelKeys;
      },
      {} as { [key in keyof ClipperModel]: IModel<M> }
    ) as M;
  }

  abstract render(): void;

  clear() {
    throw new Error("Method not implemented.");
  }
}
