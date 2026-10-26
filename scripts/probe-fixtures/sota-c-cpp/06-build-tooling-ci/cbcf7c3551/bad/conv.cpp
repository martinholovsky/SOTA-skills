int narrow(long v) {
  return static_cast<int>(v); // NOLINT(bugprone-narrowing-conversions)
}
