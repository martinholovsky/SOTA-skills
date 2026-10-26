import vm from 'node:vm';
app.post('/calc', (req, res) => {
  res.json({ result: vm.runInNewContext(req.body.expr, {}) });
});
