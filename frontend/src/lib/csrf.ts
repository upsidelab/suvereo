export function getCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function primeCsrfToken(apiBase: string): Promise<void> {
  await fetch(`${apiBase}/api/auth/csrf`, { credentials: 'include' });
}
