export function cartLabel(count: number): string {
  return "You have " + count + " item" + (count === 1 ? "" : "s");
}
