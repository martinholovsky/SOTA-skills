app.get('/preview', async (req, res) => {
  const page = await fetch(req.query.url as string);
  res.send(await page.text());
});
