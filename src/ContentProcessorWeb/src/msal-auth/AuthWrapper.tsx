
import React, { useEffect } from "react";
import { msalInstance } from "./msalInstance";
import { loginRequest } from "./msaConfig";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";

import useAuth from './useAuth';

const AuthWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {

  const { isAuthenticated, login, inProgress,token } = useAuth();
  const authEnabled = process.env.REACT_APP_AUTH_ENABLED?.toLowerCase() !== 'false'; // Defaults to true if not set

  useEffect(() => {
    if (authEnabled && !isAuthenticated && inProgress === InteractionStatus.None) {
      login();
    }
  }, [authEnabled, isAuthenticated, inProgress]);

  if (!authEnabled) {
    return <>{children}</>;
  }

  return <>{(isAuthenticated && token) && children}</>
};

export default AuthWrapper;

