router.get('/orders/:id', asyncHandler(async (req, res) => {
  res.json(await Order.get(req.params.id));
}));
