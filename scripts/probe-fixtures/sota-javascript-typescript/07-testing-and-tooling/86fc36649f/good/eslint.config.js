import tseslint from 'typescript-eslint';
export default tseslint.config(...tseslint.configs.strictTypeChecked, {
  rules: { '@typescript-eslint/no-floating-promises': 'error' },
});
