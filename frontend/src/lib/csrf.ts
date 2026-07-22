const CSRF_COOKIE_NAME = 'csrftoken';

function readCookie(name: string): string | null {
  const cookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${name}=`));

  if (!cookie) {
    return null;
  }

  return decodeURIComponent(cookie.slice(name.length + 1));
}

export function getCsrfToken(): string | null {
  return readCookie(CSRF_COOKIE_NAME);
}

export async function primeCsrfToken(apiBase: string): Promise<void> {
  const url = new URL('/api/auth/csrf', apiBase);
  await fetch(url, { credentials: 'include' });
}
