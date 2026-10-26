export function topScores(scores: readonly number[]) {
  return scores.toSorted((a, b) => b - a).slice(0, 3);
}
