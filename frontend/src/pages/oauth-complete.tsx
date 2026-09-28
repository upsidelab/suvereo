import { useEffect } from "react";

export const OAUTH_CHANNEL = "enthusiast-oauth";

export function OAuthCompletePage() {
  useEffect(() => {
    const state = new URLSearchParams(window.location.search).get("state") ?? "";
    const channel = new BroadcastChannel(OAUTH_CHANNEL);
    channel.postMessage({ state });
    channel.close();
    window.close();
  }, []);

  return (
    <div className="p-8 text-sm text-muted-foreground">
      Finished. You can close this window and return to the form.
    </div>
  );
}
