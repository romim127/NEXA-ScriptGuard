import js from '@eslint/js';
import hooks from 'eslint-plugin-react-hooks';
import ts from 'typescript-eslint';

export default ts.config(
  { ignores: ['**/playwright-report/**', '**/test-results/**'] },
  js.configs.recommended,
  ...ts.configs.recommended,
  {
    files: ['**/*.{ts,tsx}'],
    plugins: { 'react-hooks': hooks },
    rules: { 'react-hooks/rules-of-hooks': 'error', 'react-hooks/exhaustive-deps': 'error' },
  },
);
