/** Authenticated fetch helper for the SentinelText API. */
export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const form = init.body instanceof FormData;
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(form ? {} : { 'Content-Type': 'application/json' }),
      ...(init.headers || {}),
    },
  });

  if (!response.ok) {
    if (response.status === 401 && path !== '/auth/me') {
      window.dispatchEvent(new Event('sentinel:unauthorized'));
    }
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}
