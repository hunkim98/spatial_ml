export abstract class IModel<T> {
  reset() {
    throw new Error("reset method is not implemented");
  }

  update(data: Partial<T>) {
    for (const key in data) {
      this[key as keyof this] = data[key] as this[keyof this];
    }
  }
}
