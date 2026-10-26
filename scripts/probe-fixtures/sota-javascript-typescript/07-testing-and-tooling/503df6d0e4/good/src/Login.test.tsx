it('submits', async () => {
  render(<Login />);
  await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
  expect(onSubmit).toHaveBeenCalled();
});
