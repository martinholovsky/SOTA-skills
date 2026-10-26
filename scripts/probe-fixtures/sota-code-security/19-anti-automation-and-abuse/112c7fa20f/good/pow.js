app.get("/pow", (req, res) => {
  const tier = riskTierFor(res.locals.clientKey);
  const difficulty = DIFFICULTY_BY_TIER[tier];
  res.json(issueChallenge(difficulty));
});
