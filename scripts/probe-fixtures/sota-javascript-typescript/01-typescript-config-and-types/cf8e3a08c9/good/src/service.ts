export class BillingService {
  readonly #repo: Repo;
  constructor(repo: Repo) {
    this.#repo = repo;
  }
}
