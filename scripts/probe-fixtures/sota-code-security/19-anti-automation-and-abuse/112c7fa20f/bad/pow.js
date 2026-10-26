app.get("/pow", (req, res) => {
  const difficulty = Number(req.query.difficulty) || 20;
  res.json(issueChallenge(difficulty));
});
