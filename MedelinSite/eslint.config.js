const js = require('@eslint/js');

const browserGlobals = {
    window: 'readonly',
    document: 'readonly',
    navigator: 'readonly',
    location: 'readonly',
    localStorage: 'readonly',
    sessionStorage: 'readonly',
    fetch: 'readonly',
    FormData: 'readonly',
    URLSearchParams: 'readonly',
    setTimeout: 'readonly',
    clearTimeout: 'readonly',
    alert: 'readonly',
    console: 'readonly',
    L: 'readonly',
};

module.exports = [
    {
        ignores: ['images*.min.js'],
    },
    {
        files: ['js*.js'],
        languageOptions: {
            ecmaVersion: 'latest',
            sourceType: 'script',
            globals: browserGlobals,
        },
        rules: {
            ...js.configs.recommended.rules,
            'no-empty': ['error', { allowEmptyCatch: true }],
            'no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
            'prefer-const': 'warn',
        },
    },
];
