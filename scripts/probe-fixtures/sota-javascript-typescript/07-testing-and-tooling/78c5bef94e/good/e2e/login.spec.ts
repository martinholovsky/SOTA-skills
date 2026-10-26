test('login', async ({ page }) => {
  await page.getByLabel('Email').fill('a@example.com');
  await page.getByRole('button', { name: 'Sign in' }).click();
});
