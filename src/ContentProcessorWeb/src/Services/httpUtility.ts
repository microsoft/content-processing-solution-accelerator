// Copyright (c) Microsoft Corporation.
// Licensed under the MIT License.

/**
 * HTTP utility layer that wraps the Fetch API with JWT-based authentication.
 *
 * Provides `httpUtility.get/post/put/delete/upload/login/headers` methods
 * consumed by Redux async thunks across the application.
 */

const api: string = process.env.REACT_APP_API_BASE_URL as string;

interface FetchResponse<T> {
  data: T | null;
  status: number;
}

interface FetchOptions {
  method: string;
  headers: HeadersInit;
  body?: string | FormData | null;
}

interface ApiError {
  data: { message?: string } | null;
  status: number;
  message?: string;
}

/**
 * Wraps an async API call for use inside a Redux `createAsyncThunk`.
 *
 * Returns the response data on 200/202, or calls `rejectWithValue` with
 * a descriptive error message on failure.
 *
 * @param apiCall - The promise returned by `httpUtility.get/post/put/delete`.
 * @param rejectWithValue - The thunk's `rejectWithValue` callback.
 * @param errorMessage - A human-readable fallback error message.
 * @param endpoint - Optional API path used for logging.
 * @returns The unwrapped response data of type `T`.
 */
export const handleApiThunk = async <T>(
  apiCall: Promise<{ data: T | null; status: number }>,
  rejectWithValue: (reason: string) => unknown,
  errorMessage = 'Request failed',
  endpoint?: string
): Promise<T> => {
  try {
    const response = await apiCall;
    const endpointName = endpoint ? endpoint.split('/').filter(Boolean).pop() : 'unknown';
    console.log(`API Response [${endpointName}]:`, response);
    if (response.status === 200 || response.status === 202) {
      return response.data as T;
    } else {
      return rejectWithValue(`${errorMessage}. Status: ${response.status}`);
    }
  } catch (error: unknown) {
    const apiError = error as ApiError;
    if (apiError.status === 415 || apiError.status === 404) {
      return rejectWithValue(apiError.data?.message || `Unexpected error: ${errorMessage}`);
    }
    return rejectWithValue(apiError.message || `Unexpected error: ${errorMessage}`);
  }
};


/** Performs an authenticated fetch and returns parsed JSON with status. */
const fetchWithAuth = async <T>(
  url: string,
  method: string = 'GET',
  body: BodyInit | Record<string, unknown> | null = null
): Promise<FetchResponse<T>> => {
  const token = localStorage.getItem('token');

  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
  };

  let processedBody: BodyInit | null = null;
  if (body instanceof FormData) {
    processedBody = body;
  } else if (body) {
    headers['Content-Type'] = 'application/json';
    processedBody = JSON.stringify(body);
  }

  const options: RequestInit = {
    method,
    headers,
  };

  if (processedBody) {
    options.body = processedBody;
  }

  try {
    const response = await fetch(`${api}${url}`, options);

    const status = response.status;
    const isJson = response.headers.get('content-type')?.includes('application/json');

    const data = isJson ? await response.json() : null;

    if (!response.ok) {
      throw { data, status };
    }

    return { data, status };
  } catch (error: unknown) {
    const apiError = error as ApiError;
    if (apiError?.status !== undefined) {
      throw error;
    }
    const isOffline = !navigator.onLine;

    const message = isOffline
      ? 'No internet connection. Please check your network and try again.'
      : 'Unable to connect to the server. Please try again later.';

    throw { data: null, status: 0, message };
  }
};

/** Performs an authenticated fetch and returns the raw `Response` (for blob / header access). */
const fetchHeadersWithAuth = async <T>(
  url: string,
  method: string = 'GET',
  body: BodyInit | Record<string, unknown> | null = null
): Promise<Response> => {
  const token = localStorage.getItem('token');

  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
  };

  if (body instanceof FormData) {
    delete headers['Content-Type'];
  } else {
    headers['Content-Type'] = 'application/json';
    body = body ? JSON.stringify(body as Record<string, unknown>) : null;
  }

  const options: FetchOptions = {
    method,
    headers,
  };

  if (body) {
    options.body = body as string | FormData;
  }

  const response = await fetch(`${api}${url}`, options);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Something went wrong');
  }
  return response;
};

/** Performs an unauthenticated fetch (used for the login flow). */
const fetchWithoutAuth = async <T>(
  url: string,
  method: string = 'POST',
  body: Record<string, unknown> | null = null
): Promise<T | null> => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const options: FetchOptions = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${api}${url}`, options);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || 'Login failed');
  }

  const isJson = response.headers.get('content-type')?.includes('application/json');
  return isJson ? (await response.json()) as T : null;
};

/** Convenience wrapper exposing typed HTTP methods for the application. */
export const httpUtility = {
  get: <T>(url: string): Promise<FetchResponse<T>> => fetchWithAuth<T>(url, 'GET'),
  post: <T>(url: string, body: Record<string, unknown>): Promise<FetchResponse<T>> => fetchWithAuth<T>(url, 'POST', body),
  put: <T>(url: string, body: Record<string, unknown>): Promise<FetchResponse<T>> => fetchWithAuth<T>(url, 'PUT', body),
  delete: <T>(url: string): Promise<FetchResponse<T>> => fetchWithAuth<T>(url, 'DELETE'),
  upload: <T>(url: string, formData: FormData): Promise<FetchResponse<T>> => fetchWithAuth<T>(url, 'POST', formData),
  login: <T>(url: string, body: Record<string, unknown>): Promise<T | null> => fetchWithoutAuth<T>(url, 'POST', body),
  headers: <T>(url: string): Promise<Response> => fetchHeadersWithAuth<T>(url, 'GET'),
};

export default httpUtility;
