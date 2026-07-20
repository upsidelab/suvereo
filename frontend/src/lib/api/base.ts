import { AuthenticationProvider } from "@/lib/authentication-provider.ts";
import { getCsrfToken } from "@/lib/csrf.ts";

export abstract class BaseApiClient {
  constructor(protected readonly apiBase: string, protected readonly authenticationProvider: AuthenticationProvider) {}

  _requestConfiguration(): RequestInit {
    return {
      credentials: 'include',
      headers: {
        'X-CSRFToken': getCsrfToken() ?? '',
        "Content-Type": "application/json"
      }
    }
  }
}
