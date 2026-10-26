it('toggles', () => {
  render(<Toggle />);
  fireEvent.click(screen.getByRole('switch'));
  expect(screen.getByRole('switch')).toBeChecked();
});
