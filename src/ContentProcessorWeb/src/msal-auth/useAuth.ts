// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * Custom hook that exposes MSAL authentication state and actions
 * (login, logout, token acquisition) to React components.
 *
 * @returns Authentication state and helper functions.
 */
import { useState, useEffect, useCallback } from 'react';

import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus, AccountInfo } from "@azure/msal-browser";

import { getMsalInstanceSync } from "./msalInstance";
import { loginRequest, tokenRequest } from "./msaConfig";

interface User {
  username: string;
  name: string | undefined;
  shortName?: string;
  isInTeams: boolean;
}

const useAuth = () => {
  const { instance, accounts } = useMsal();
  const [user, setUser] = useState<User | null>(null);

  const { inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [token, setToken] = useState<string | null>(null);

  const activeAccount: AccountInfo | undefined = accounts[0];

  const getToken = useCallback(async () => {
    const active = instance.getActiveAccount();
    if (!active) {
      console.error("No active account set. Please log in.");
      return;
    }

    try {
      const accessTokenRequest = {
        scopes: [...tokenRequest.scopes],
        account: active,
      };

      const response = await instance.acquireTokenSilent(accessTokenRequest);
      const accessToken = response.accessToken;
      localStorage.setItem('token', accessToken);
      setToken(accessToken);
    } catch (error) {
      console.error("Error acquiring token:", error);
    }
  }, [instance]);

  useEffect(() => {
    if (accounts.length > 0) {
      setUser({
        username: accounts[0].username,
        name: accounts[0]?.name,
        isInTeams: false,
      });
      instance.setActiveAccount(accounts[0]);
      getToken();
    }
  }, [accounts, instance, getToken]);

  const login = useCallback(async () => {
    const msalInst = getMsalInstanceSync();
    if (!msalInst) return;
    const allAccounts = msalInst.getAllAccounts();
    if (allAccounts.length === 0 && inProgress === InteractionStatus.None) {
      try {
        await msalInst.loginRedirect(loginRequest);
      } catch (error) {
        console.error("Login failed:", error);
      }
    }
  }, [inProgress]);

  const logout = useCallback(async () => {
    if (activeAccount) {
      try {
        await instance.logoutRedirect({
          account: activeAccount,
        });
        localStorage.removeItem('token');
      } catch (error) {
        console.error("Logout failed:", error);
      }
    } else {
      console.warn("No active account found for logout.");
    }
  }, [activeAccount, instance]);

  return {
    isAuthenticated,
    login,
    logout,
    user,
    accounts,
    inProgress,
    token,
    getToken,
  };
};

export default useAuth;
