test('checkout', async ({ page }) => {
  await page.click('text=Pay');
  await page.waitForTimeout(3000);
  await expect(page.getByText('Thanks')).toBeVisible();
});
