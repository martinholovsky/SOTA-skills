import { Parser } from 'expr-eval';
const parser = new Parser();
app.post('/calc', (req, res) => {
  res.json({ result: parser.evaluate(Expr.parse(req.body).expr) });
});
