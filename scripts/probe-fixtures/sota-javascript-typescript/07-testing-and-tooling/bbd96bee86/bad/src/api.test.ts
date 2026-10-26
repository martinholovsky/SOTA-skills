it('lists users', async () => {
  const res = await fetch('http://localhost:3000/api/users');
  expect(res.ok).toBe(true);
});
