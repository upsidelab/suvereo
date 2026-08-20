import { cn } from "@/lib/utils"
import { Input } from "@/components/ui/input.tsx";
import { Button } from "@/components/ui/button.tsx";
import { HTMLAttributes, SyntheticEvent, useState } from "react";
import { Spinner } from "@/components/util/spinner.tsx";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { useNavigate } from "react-router-dom";
import { ApiClient } from "@/lib/api.ts";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert.tsx";
import { PERMISSIONS } from "@/lib/permissions.ts";

const api = new ApiClient(authenticationProviderInstance);

async function firstAgentId(dataSetId: number): Promise<number | undefined> {
  try {
    const agents = await api.agents().getDatasetAvailableAgents(dataSetId);
    return agents?.[0]?.id;
  } catch {
    // Listing agents needs `agent.view`, which a signed-in user may not hold.
    return undefined;
  }
}

/**
 * Where to send a user who has just signed in: straight into a conversation when they can hold
 * one, and the start page otherwise - `protectedLoginLoader` decides from there, so no permission
 * rule is duplicated here.
 */
async function landingPage(): Promise<string> {
  const dataSets = await api.dataSets().getDataSets();
  const dataSet = dataSets[0];

  if (!dataSet || !dataSet.permissions.includes(PERMISSIONS.CONVERSATION.CONVERSE)) {
    return '/';
  }

  const agentId = await firstAgentId(dataSet.id!);
  return agentId
    ? `/data-sets/${dataSet.id}/chat/new/${agentId}`
    : `/data-sets/${dataSet.id}/chat/new`;
}

export function LoginForm({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const navigate = useNavigate();

  async function onSubmit(event: SyntheticEvent) {
    event.preventDefault();
    setIsLoading(true);

    const email = (event.target as HTMLFormElement).email.value;
    const password = (event.target as HTMLFormElement).password.value;

    try {
      const { token } = await api.login(email, password);
      authenticationProviderInstance.login(token);
    } catch {
      setIsError(true);
      setIsLoading(false);
      return;
    }

    try {
      navigate(await landingPage());
    } catch {
      // Signing in worked, so this is never a credentials error - the root loader takes over from
      // the start page.
      navigate('/');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className={cn("grid gap-6", className)} {...props}>
      <form onSubmit={onSubmit}>
        <div className="grid gap-2">
          <div className="grid gap-1">
            {isError && <Alert variant="destructive">
              <AlertTitle>Invalid email or password</AlertTitle>
              <AlertDescription>Make sure that the credentials that you've provided are correct and try again.</AlertDescription>
            </Alert>}
            <Input
              id="email"
              placeholder="user@example.com"
              type="email"
              autoCapitalize="none"
              autoComplete="email"
              autoCorrect="off"
              disabled={isLoading}
            />
            <Input
              id="password"
              placeholder="password"
              type="password"
              autoCapitalize="none"
              autoComplete="off"
              autoCorrect="off"
              disabled={isLoading}
            />
          </div>
          <Button disabled={isLoading}>
            {isLoading && (
              <Spinner />
            )}
            Continue
          </Button>
        </div>
      </form>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t"/>
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            Or
          </span>
        </div>
      </div>
      <Button disabled variant="outline">
        Log in with SSO
      </Button>
    </div>
  )
}
