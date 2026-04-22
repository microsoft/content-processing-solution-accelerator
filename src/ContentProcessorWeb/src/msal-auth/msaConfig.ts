// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * MSAL configuration, login scopes, token request scopes,
 * and Microsoft Graph endpoint used for authentication.
 */
import { Configuration, LogLevel } from '@azure/msal-browser';

const isUsableScope = (scope?: string): scope is string => {
  if (!scope) return false;
  const value = scope.trim();
  if (!value) return false;
  // Guard against unresolved placeholders from env substitution.
  if (value.startsWith('APP_')) return false;
  if (value.startsWith('<') && value.endsWith('>')) return false;
  return true;
};

export const msalConfig: Configuration = {
  auth: {
    clientId: process.env.REACT_APP_WEB_CLIENT_ID as string,
    authority: process.env.REACT_APP_WEB_AUTHORITY,
    redirectUri: process.env.REACT_APP_REDIRECT_URL as string,
    postLogoutRedirectUri: process.env.REACT_APP_POST_REDIRECT_URL as string,
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return;
        if (level === LogLevel.Error) console.error(message);
      },
    },
  },
};

const loginScope = process.env.REACT_APP_WEB_SCOPE as string;
const tokenScope = process.env.REACT_APP_API_SCOPE as string;

const loginScopes = ['user.read'];
if (isUsableScope(loginScope)) {
  loginScopes.push(loginScope);
}

const tokenScopes = isUsableScope(tokenScope)
  ? [tokenScope]
  : isUsableScope(loginScope)
    ? [loginScope]
    : ['user.read'];

export const loginRequest = {
  scopes: loginScopes,
};

export const graphConfig = {
  graphMeEndpoint: "https://graph.microsoft.com/v1.0/me",
};

export const tokenRequest = {
  scopes: tokenScopes,
};