import {
  PatternSelectorEvent,
  PatternSelectorEventListeners,
} from "../events";
import { PatternSelectorModel } from "../model";
import { IModel } from "../model/base";
import { PatternSelectorView } from "../view";

export abstract class BaseController<
  M extends Partial<PatternSelectorModel>,
  V extends Partial<PatternSelectorView>,
  P,
> {
  models: M;
  views: V;
  listeners: PatternSelectorEventListeners;

  constructor(
    models: PatternSelectorModel,
    views: PatternSelectorView,
    listeners: PatternSelectorEventListeners
  ) {
    const neededModelKeys = Object.keys(models) as Array<
      keyof PatternSelectorModel
    >;
    const neededViewKeys = Object.keys(views) as Array<
      keyof PatternSelectorView
    >;

    this.models = neededModelKeys.reduce(
      (modelKeys, key) => {
        modelKeys[key] = models[key] as IModel<M>;
        return modelKeys;
      },
      {} as { [key in keyof PatternSelectorModel]: IModel<M> }
    ) as M;
    this.views = neededViewKeys.reduce(
      (viewKeys, key) => {
        viewKeys[key] = views[key] as unknown;
        return viewKeys;
      },
      {} as { [key in keyof PatternSelectorView]: unknown }
    ) as V;
    this.listeners = listeners;
  }

  abstract execute(params: P): void;

  dispatchEvent(eventName: PatternSelectorEvent) {
    const listeners = this.listeners[eventName];
    if (listeners) {
      listeners.forEach((listener) =>
        listener(this.models as Partial<PatternSelectorModel>)
      );
    }
  }
}
