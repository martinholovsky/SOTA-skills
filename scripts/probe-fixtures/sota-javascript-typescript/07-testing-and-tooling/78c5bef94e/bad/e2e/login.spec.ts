test('login', async ({ page }) => {
  await page.locator('#email').fill('a@example.com');
  await page.locator('.submit-btn').click();
});
