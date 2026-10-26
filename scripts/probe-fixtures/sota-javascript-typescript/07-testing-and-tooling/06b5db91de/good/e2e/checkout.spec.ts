test('checkout', async ({ page }) => {
  await page.getByRole('button', { name: 'Pay' }).click();
  await expect(page.getByText('Thanks')).toBeVisible();
});
