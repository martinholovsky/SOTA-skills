app.get('/page', (req, res) => {
  res.render(req.query.view, { user: req.user });
});
