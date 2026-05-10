import { PatternSelectorModel } from "../model";
import { IModel } from "../model/base";

export abstract class IView<M> {
  models: M;

  constructor(models: PatternSelectorModel) {
    const neededModelKeys = Object.keys(models) as Array<
      keyof PatternSelectorModel
    >;

    this.models = neededModelKeys.reduce(
      (modelKeys, key) => {
        modelKeys[key] = models[key] as IModel<M>;
        return modelKeys;
      },
      {} as { [key in keyof PatternSelectorModel]: IModel<M> }
    ) as M;
  }

  abstract render(): void;

  clear() {
    throw new Error("Method not implemented.");
  }
}
