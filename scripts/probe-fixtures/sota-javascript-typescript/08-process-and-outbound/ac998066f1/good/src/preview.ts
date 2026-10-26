app.get('/preview', async (req, res) => {
  const target = await assertPublicUrl(String(req.query.url));
  const page = await fetch(target, { redirect: 'error', dispatcher: guardedAgent });
  res.send(await page.text());
});
