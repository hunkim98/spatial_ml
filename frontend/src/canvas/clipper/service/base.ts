export abstract static class IService<P, R> {
  static serve(params: P): R {
    throw new Error("Method not implemented.");
  }
}
