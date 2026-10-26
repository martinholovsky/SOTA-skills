const VIEWS = new Set(['home', 'about']);
app.get('/page', (req, res) => {
  const view = VIEWS.has(String(req.query.view)) ? String(req.query.view) : 'home';
  res.render(view, { user: req.user });
});
