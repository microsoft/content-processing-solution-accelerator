// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Top-level MSAL authentication provider that wraps the application
 * in an `MsalProvider` and the login-redirect `AuthWrapper`.
 *
 * When authentication is disabled (`REACT_APP_AUTH_ENABLED=false`),
 * MSAL is never loaded and children render immediately.
 */
import React, { useEffect, useState } from 'react';

import { MsalProvider } from '@azure/msal-react';
import { PublicClientApplication } from '@azure/msal-browser';

import { getMsalInstance } from './msalInstance';
import AuthWrapper from './AuthWrapper';

interface AuthProviderProps {
  /** Child elements rendered only after authentication succeeds. */
  readonly children: React.ReactNode;
}

const isAuthEnabled = (): boolean =>
  process.env.REACT_APP_AUTH_ENABLED?.toLowerCase() !== 'false';

const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const authEnabled = isAuthEnabled();
  const [msalInstance, setMsalInstance] = useState<PublicClientApplication | null>(null);
  const [initError, setInitError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getMsalInstance()
      .then((instance) => {
        if (!cancelled) setMsalInstance(instance);
      })
      .catch((err) => {
        console.error('MSAL initialisation failed:', err);
        if (!cancelled) setInitError(String(err));
      });

    return () => { cancelled = true; };
  }, []);

  // Still loading MSAL instance
  if (!msalInstance) {
    if (initError) {
      return <div style={{ padding: 24, color: 'red' }}>Authentication failed to initialise: {initError}</div>;
    }
    return null;
  }

  // Always wrap in MsalProvider so useMsal() hooks work everywhere.
  // When auth is disabled, skip the AuthWrapper login gate.
  return (
    <MsalProvider instance={msalInstance}>
      {authEnabled ? <AuthWrapper>{children}</AuthWrapper> : <>{children}</>}
    </MsalProvider>
  );
};

export default AuthProvider;
