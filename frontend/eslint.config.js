import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'src/components/ui'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      'no-restricted-globals': [
        'error',
        { name: 'fetch', message: 'Call the server through ApiClient (src/lib/api.ts), see frontend/AGENTS.md.' },
      ],
      'no-restricted-syntax': [
        'error',
        {
          selector: 'CallExpression[callee.name=/^has(DataSet)?Permission$/] > Literal',
          message: 'Use a PERMISSIONS constant from src/lib/permissions/codes.ts, see frontend/AGENTS.md.',
        },
      ],
      'no-restricted-imports': [
        'error',
        {
          patterns: [{
            group: ['@mui/*', '@chakra-ui/*', 'antd', 'antd/*', '@mantine/*', 'react-bootstrap', 'bootstrap'],
            message: 'Build UI from src/components/ui and src/components/util, see frontend/AGENTS.md.',
          }],
        },
      ],
    },
  },
  {

    files: ['src/lib/**/*.ts'],
    rules: { 'no-restricted-globals': 'off' },
  },
)
