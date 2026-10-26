it('submits', async () => {
  const { container } = render(<Login />);
  await userEvent.click(container.querySelector('.btn-primary')!);
  expect(onSubmit).toHaveBeenCalled();
});
