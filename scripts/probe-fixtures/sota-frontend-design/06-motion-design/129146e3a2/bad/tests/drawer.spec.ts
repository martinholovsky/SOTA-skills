test('drawer opens', async ({ page }) => {
  await page.goto('/');
  await page.click('#open');
});
