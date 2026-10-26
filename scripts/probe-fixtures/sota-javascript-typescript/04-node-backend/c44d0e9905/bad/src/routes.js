router.get('/orders/:id', async (req, res) => {
  res.json(await Order.get(req.params.id));
});
