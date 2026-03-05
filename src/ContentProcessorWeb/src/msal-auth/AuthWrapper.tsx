// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Conditionally triggers MSAL login and gates child rendering
 * until the user is authenticated and a token is available.
 */
import React, { useEffect } from "react";

import { InteractionStatus } from "@azure/msal-browser";

import useAuth from './useAuth';

interface AuthWrapperProps {
  /** Child elements rendered only after successful authentication. */
  readonly children: React.ReactNode;
}

const AuthWrapper: React.FC<AuthWrapperProps> = ({ children }) => {
  const { isAuthenticated, login, inProgress, token } = useAuth();
  const authEnabled = process.env.REACT_APP_AUTH_ENABLED?.toLowerCase() !== 'false';

  useEffect(() => {
    if (authEnabled && !isAuthenticated && inProgress === InteractionStatus.None) {
      login();
    }
  }, [authEnabled, isAuthenticated, inProgress, login]);

  if (!authEnabled) {
    return <>{children}</>;
  }

  return <>{(isAuthenticated && token) && children}</>;
};

export default AuthWrapper;
