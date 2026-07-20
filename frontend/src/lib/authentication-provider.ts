import { getCsrfToken } from "@/lib/csrf.ts";

export interface AuthenticationProvider {
  logout(): Promise<void>;
}

class DummyAuthenticationProvider implements AuthenticationProvider {
  async logout(): Promise<void> {
    await fetch(`${import.meta.env.VITE_API_BASE}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCsrfToken() ?? '',
      },
    });
  }
}

export const authenticationProviderInstance: AuthenticationProvider = new DummyAuthenticationProvider();
