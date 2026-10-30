export type TokenPair = {
  access: string;
  refresh: string;
}

export type SessionEndReason = "expired" | "signedOutElsewhere";

export class SessionExpiredError extends Error {
  constructor() {
    super("The session has expired");
  }
}

export interface AuthenticationProvider {
  readonly accessToken: string | null;
  readonly refreshToken: string | null;
  isAuthenticated(): boolean;
  login(tokens: TokenPair): void;
  logout(): void;
  refreshAccessToken(): Promise<void>;
  invalidateSession(): void;
  onSessionEnded(handler: (reason: SessionEndReason) => void): void;
}

const refreshTokenKey = 'refreshToken';
const legacyApiKeyKey = 'token';
const refreshLockName = 'auth-refresh';

/**
 * Keeps the access token in memory only and the refresh token in `localStorage`, shared by all tabs.
 */
class TokenAuthenticationProvider implements AuthenticationProvider {
  accessToken: string | null = null;
  private pendingRefresh: Promise<void> | null = null;
  private sessionEndedHandler: ((reason: SessionEndReason) => void) | null = null;

  constructor(private readonly apiBase: string) {
    localStorage.removeItem(legacyApiKeyKey);
    window.addEventListener('storage', (event) => {
      if (event.key === refreshTokenKey && event.newValue === null) {
        this.accessToken = null;
        this.sessionEndedHandler?.("signedOutElsewhere");
      }
    });
  }

  get refreshToken(): string | null {
    return localStorage.getItem(refreshTokenKey);
  }

  isAuthenticated(): boolean {
    return this.refreshToken !== null;
  }

  login({ access, refresh }: TokenPair): void {
    this.accessToken = access;
    localStorage.setItem(refreshTokenKey, refresh);
  }

  logout(): void {
    this.accessToken = null;
    localStorage.removeItem(refreshTokenKey);
  }

  refreshAccessToken(): Promise<void> {
   // only one token rotation (thanks to `??=` operator) can be performed at a time for an AuthenticationProvider instance
    this.pendingRefresh ??= this.withRefreshLock(() => this.rotateTokens()).finally(() => {
      this.pendingRefresh = null;
    });
    return this.pendingRefresh;
  }

  invalidateSession(): void {
    if (this.isAuthenticated()) {
      this.expireSession();
    }
  }

  onSessionEnded(handler: (reason: SessionEndReason) => void): void {
    this.sessionEndedHandler = handler;
  }

  private withRefreshLock(callback: () => Promise<void>): Promise<void> {
    // `navigator.locks` exists in secure contexts only (i.e. https connection);
    // It is used to prevent race condition between multiple open browser tabs.
    // Since separate tabs do not share the AuthenticationProvider instance, the race condition check in
    // refreshAccessToken would not work in multi-tab scenario.
    return navigator.locks ? navigator.locks.request(refreshLockName, callback) : callback();
  }

  private async rotateTokens(): Promise<void> {
    // Read inside the lock - a tab that held it before this one has already rotated the token.
    const refresh = this.refreshToken;
    if (refresh === null) {
      throw this.expireSession();
    }

    const response = await fetch(`${this.apiBase}/api/auth/token/refresh`, {
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
      body: JSON.stringify({ refresh })
    });

    if (response.status === 401) {
      throw this.expireSession();
    }
    if (!response.ok) {
      throw new Error(`Failed to refresh the session: ${response.statusText}`);
    }

    this.login(await response.json() as TokenPair);
  }

  private expireSession(): SessionExpiredError {
    this.logout();
    this.sessionEndedHandler?.("expired");
    return new SessionExpiredError();
  }
}

export const authenticationProviderInstance: AuthenticationProvider =
  new TokenAuthenticationProvider(import.meta.env.VITE_API_BASE);
