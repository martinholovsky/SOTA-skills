it('toggles', async () => {
  render(<Toggle />);
  await userEvent.click(screen.getByRole('switch'));
  expect(screen.getByRole('switch')).toBeChecked();
});
