export class Client {
  #key;
  constructor(key) {
    this.#key = key;
    this.secretFn = () => 1;
  }
}
