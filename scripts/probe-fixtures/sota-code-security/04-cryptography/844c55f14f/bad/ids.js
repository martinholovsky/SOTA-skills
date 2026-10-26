function newId() {
  try {
    return crypto.randomUUID();
  } catch (e) {
    return Math.random().toString(36).slice(2);
  }
}
