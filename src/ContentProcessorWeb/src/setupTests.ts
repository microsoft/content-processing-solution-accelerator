// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * @file Jest setup — extends `expect` with jest-dom matchers and provides
 * global test helpers (e.g., `toBeInTheDocument`, `toHaveClass`).
 *
 * This file is automatically loaded by CRA before every test suite.
 */

/* eslint-disable @typescript-eslint/no-require-imports */
// Polyfill TextEncoder/TextDecoder for jsdom (required by React Router).
const { TextEncoder, TextDecoder } = require('util');

if (typeof globalThis.TextEncoder === 'undefined') {
    globalThis.TextEncoder = TextEncoder;
}
if (typeof globalThis.TextDecoder === 'undefined') {
    globalThis.TextDecoder = TextDecoder;
}

import '@testing-library/jest-dom';
