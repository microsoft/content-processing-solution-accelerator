// AuthService.ts

const api: string = process.env.REACT_APP_API_BASE_URL as string; // base API URL

// Define the types for the response
interface FetchResponse<T> {
  data: T | null;
  status: number;
}

interface FetchOptions {
  method: string;
  headers: HeadersInit;
  body?: string | FormData | null;
}

export const handleApiThunk = async <T>(
  apiCall: Promise<{ data: T | null; status: number }>,
  rejectWithValue: (reason: any) => any,
  errorMessage = 'Request failed'
): Promise<T | any> => {
  try {
    const response = await apiCall;
    console.log("API Response : ", response);
    if (response.status === 200 || response.status === 202) {
      return response.data;
    } else {
      return rejectWithValue(`${errorMessage}. Status: ${response.status}`);
    }
  } catch (error: any) {
    if (error.status == 415 || error.status == 404)
      return rejectWithValue(error.data.message || `Unexpected error: ${errorMessage}`);
    return rejectWithValue(error.message || `Unexpected error: ${errorMessage}`);
  }
};


// Fetch with JWT Authentication

const fetchWithAuth = async <T>(
  url: string,
  method: string = 'GET',
  body: any = null
): Promise<FetchResponse<T>> => {
  const token = localStorage.getItem('token');

  const headers: HeadersInit = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
  };

  if (!(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
    body = body ? JSON.stringify(body) : null;
  }

  const options: RequestInit = {
    method,
    headers,
  };

  if (body) {
    options.body = body;
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
  } catch (error: any) {
    if (error?.status !== undefined) {
      throw error;
    }
    const isNetworkError = error instanceof TypeError && error.message === 'Failed to fetch';
    const isOffline = !navigator.onLine; //isNetworkError ||

    const message = isOffline
      ? 'No internet connection. Please check your network and try again.'
      : 'Unable to connect to the server. Please try again later.';

    throw { data: null, status: 0, message };
  }
};

// Fetch with JWT Authentication
const fetchHeadersWithAuth = async <T>(url: string, method: string = 'GET', body: any = null): Promise<any> => {
  const token = localStorage.getItem('token'); // Get the token from localStorage

  const headers: HeadersInit = {
    'Authorization': `Bearer ${token}`, // Add the token to the Authorization header
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Cache-Control': 'no-cache',
  };

  // If body is FormData, do not set Content-Type header
  if (body instanceof FormData) {
    delete headers['Content-Type'];
  } else {
    headers['Content-Type'] = 'application/json';
    body = body ? JSON.stringify(body) : null;
  }

  const options: FetchOptions = {
    method,
    headers,
  };

  if (body) {
    options.body = body; // Add the body only if it exists (for POST, PUT)
  }

  try {
    const response = await fetch(`${api}${url}`, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Something went wrong');
    }
    return response;

  } catch (error: any) {
    //console.error('API Error:', error.message);
    throw error;
  }
};

// Vanilla Fetch without Auth for Login
const fetchWithoutAuth = async <T>(url: string, method: string = 'POST', body: any = null): Promise<T | null> => {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };

  const options: FetchOptions = {
    method,
    headers,
  };

  if (body) {
    options.body = JSON.stringify(body); // Add the body for POST
  }

  try {
    const response = await fetch(`${api}${url}`, options);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || 'Login failed');
    }

    const isJson = response.headers.get('content-type')?.includes('application/json');
    return isJson ? (await response.json()) as T : null;
  } catch (error: any) {
    //console.error('Login Error:', error.message);
    throw error;
  }
};

// Authenticated requests (with token) and login (without token)
export const httpUtility = {
  get: <T>(url: string): Promise<{ data: T | null; status: number }> => fetchWithAuth<T>(url, 'GET'),
  post: <T>(url: string, body: any): Promise<{ data: T | null; status: number }> => fetchWithAuth<T>(url, 'POST', body),
  put: <T>(url: string, body: any): Promise<{ data: T | null; status: number }> => fetchWithAuth<T>(url, 'PUT', body),
  delete: <T>(url: string): Promise<{ data: T | null; status: number }> => fetchWithAuth<T>(url, 'DELETE'),
  upload: <T>(url: string, formData: FormData): Promise<{ data: T | null; status: number }> => fetchWithAuth<T>(url, 'POST', formData),
  login: <T>(url: string, body: any): Promise<T | null> => fetchWithoutAuth<T>(url, 'POST', body), // For login without auth
  headers: <T>(url: string): Promise<any> => fetchHeadersWithAuth<T>(url, 'GET'),
};

export default httpUtility;
