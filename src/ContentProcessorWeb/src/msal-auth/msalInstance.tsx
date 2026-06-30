// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Creates and initialises the singleton MSAL `PublicClientApplication` instance
 * shared across the authentication layer.
 *
 * Initialisation is deferred until {@link getMsalInstance} is called so the
 * app can start even when auth is disabled and MSAL config values are empty.
 */
import { PublicClientApplication } from "@azure/msal-browser";

import { msalConfig } from "./msaConfig";

let msalInstance: PublicClientApplication | null = null;

/**
 * Lazily creates, initialises and returns the MSAL instance.
 * When config values are missing (e.g. auth is disabled), a safe
 * fallback `clientId` is used so MSAL initialises without crashing.
 */
export async function getMsalInstance(): Promise<PublicClientApplication> {
  if (!msalInstance) {
    const safeConfig = {
      ...msalConfig,
      auth: {
        ...msalConfig.auth,
        // MSAL requires a non-empty clientId; use a placeholder when auth is disabled
        clientId: msalConfig.auth.clientId || 'auth-disabled',
      },
    };
    msalInstance = new PublicClientApplication(safeConfig);
    await msalInstance.initialize();
  }
  return msalInstance;
}

/**
 * Returns the already-initialised instance **synchronously**.
 * Call {@link getMsalInstance} first to ensure it is ready.
 */
export function getMsalInstanceSync(): PublicClientApplication | null {
  return msalInstance;
}
