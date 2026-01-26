export abstract class IModel<T> {
  // this is a default resetter
  // you may override this method in the child class
  reset() {
    throw new Error("reset method is not implemented");
  }

  // this is the default setter
  // you may override this method in the child class
  update(data: Partial<T>) {
    // update keys inside the model
    for (const key in data) {
      this[key as keyof this] = data[key] as this[keyof this];
    }
  }
}
