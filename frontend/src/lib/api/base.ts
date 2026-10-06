import { AuthenticationProvider, SessionExpiredError } from "@/lib/authentication-provider.ts";

export abstract class BaseApiClient {
  constructor(protected readonly apiBase: string, protected readonly authenticationProvider: AuthenticationProvider) {}

  protected async authenticatedFetch(input: string, init: RequestInit = {}): Promise<Response> {
    if (this.authenticationProvider.accessToken === null) {
      await this.tryRefresh();
    }

    const sentAccessToken = this.authenticationProvider.accessToken;
    const response = await fetch(input, this.prepareAndAuthenticateRequest(init));
    if (response.status !== 401) {
      return response;
    }

    // A concurrent request may have refreshed the token while this one was in flight.
    const refreshed = this.authenticationProvider.accessToken !== sentAccessToken || await this.tryRefresh();
    return refreshed ? fetch(input, this.prepareAndAuthenticateRequest(init)) : response;
  }

  private prepareAndAuthenticateRequest(init: RequestInit): RequestInit {
    const headers = new Headers(init.headers);
    if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    const accessToken = this.authenticationProvider.accessToken;
    if (accessToken !== null) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return { ...init, headers };
  }

  private async tryRefresh(): Promise<boolean> {
    if (!this.authenticationProvider.isAuthenticated()) {
      return false;
    }

    try {
      await this.authenticationProvider.refreshAccessToken();
      return true;
    } catch (error) {
      if (error instanceof SessionExpiredError) {
        return false;
      }
      throw error;
    }
  }
}
