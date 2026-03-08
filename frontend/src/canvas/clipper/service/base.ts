export abstract class IService {
  static serve<P, R>(params: P): R {
    throw new Error("Method not implemented.");
  }
}
