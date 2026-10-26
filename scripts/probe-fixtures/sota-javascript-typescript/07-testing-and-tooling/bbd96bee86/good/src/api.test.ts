server.use(http.get('/api/users', () => HttpResponse.json([{ id: '1' }])));
it('lists users', async () => {
  expect(await listUsers()).toHaveLength(1);
});
