function newId() {
  try {
    return crypto.randomUUID();
  } catch (e) {
    throw new Error("no CSPRNG available: " + e.message);
  }
}
