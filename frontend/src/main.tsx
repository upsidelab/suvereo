import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { createBrowserRouter, LoaderFunctionArgs, redirect, RouterProvider } from "react-router-dom";
import { ChatHistory } from "@/pages/data-sets/(id)/history.tsx";
import { Chat } from "@/pages/data-sets/(id)/chat/index.tsx";
import { LoginPage } from "@/pages/login.tsx";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { ApiConnectionIndex } from "@/pages/service-accounts/index.tsx";
import { NoDataSets } from "@/pages/no-data-sets.tsx";
import { ErrorPage } from "@/pages/error.tsx";
import { ApiClient } from "@/lib/api.ts";
import { NewDataSet } from "@/pages/data-sets/new.tsx";
import { DataSetsIndex } from "@/pages/data-sets";
import { EditDataSet } from "@/pages/data-sets/(id)/edit.tsx";
import { IndexDataSetUsers } from "@/pages/data-sets/(id)/users.tsx";
import { IndexDataSetIntegrations } from "@/pages/data-sets/(id)/integrations.tsx";
import { UsersIndex } from "@/pages/users";
import { RolesIndex } from "@/pages/roles";
import { OnboardingIndex } from "@/pages/onboarding";
import AgentsPage from "@/pages/data-sets/(id)/agents";
import { AgenticExecutionsPage } from "@/pages/data-sets/(id)/agentic-executions/index.tsx";
import { AgenticExecutionDetailPage } from "@/pages/data-sets/(id)/agentic-executions/(id)/index.tsx";
import { EntityRecordsPage } from "@/pages/data-sets/(id)/entities/[slug].tsx";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";
import { ApiError } from "@/lib/api-error.ts";
import { ROOT_ROUTE_ID } from "@/lib/root-route.ts";
import { RequirePermission } from "@/components/util/require-permission.tsx";
import { NotFound } from "@/pages/not-found.tsx";

const api = new ApiClient(authenticationProviderInstance);

const NO_DATA_SETS_PATH = "/no-data-sets";

const loginLoader = async () => {
  return authenticationProviderInstance.isAuthenticated() ? redirect("/") : null;
};

const signOutAndReturnToLogin = () => {
  authenticationProviderInstance.logout();
  return redirect("/login");
};

const protectedLoginLoader = async ({ request }: LoaderFunctionArgs) => {
  if (!authenticationProviderInstance.isAuthenticated()) {
    return redirect("/login");
  }

  let apiDataSets;
  try {
    apiDataSets = await api.dataSets().getDataSets();
  } catch (loadError) {
    // A token that no longer authenticates would otherwise bounce between here and `loginLoader`.
    if (loadError instanceof ApiError && loadError.response.status === 401) {
      return signOutAndReturnToLogin();
    }
    throw loadError;
  }

  if (!apiDataSets) {
    return signOutAndReturnToLogin();
  }

  // Without a data set the index has nothing to show, so it becomes onboarding for whoever can
  // create one and the no-data-sets landing for everyone else. Every other path is left to its own
  // guard - a global screen the user holds still opens, anything else renders the 404 page.
  if (apiDataSets.length === 0 && new URL(request.url).pathname === "/") {
    const accountData = await api.getAccount();
    return redirect(accountData.permissions.includes(PERMISSIONS.DATASET.ADD) ? "/onboarding" : NO_DATA_SETS_PATH);
  }

  return { dataSets: apiDataSets };
};

const router = createBrowserRouter([
  {
    id: ROOT_ROUTE_ID,
    path: "/",
    element: <App />,
    loader: protectedLoginLoader,
    // The root match never changes id, so its loader would otherwise run on full loads only -
    // leaving its redirects unenforced and its data sets stale after a mutation.
    shouldRevalidate: () => true,
    errorElement: <ErrorPage />,
    children: [
      {
        path: "/",
        element: <Chat />
      },
      {
        path: '/data-sets/:id/chat',
        element: (
          <RequirePermission dataSetAnyOf={[PERMISSIONS.CONVERSATION.CONVERSE, PERMISSIONS.CONVERSATION.VIEW_ALL]}>
            <Chat />
          </RequirePermission>
        ),
        children: [
          { path: 'new' },
          { path: 'new/:agent' },
          { path: ':chatId' }
        ]
      },
      {
        path: '/data-sets/:id/history',
        element: (
          <RequirePermission dataSetAnyOf={[PERMISSIONS.CONVERSATION.CONVERSE, PERMISSIONS.CONVERSATION.VIEW_ALL]}>
            <ChatHistory />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets',
        element: <DataSetsIndex />
      },
      {
        path: '/data-sets/new',
        element: (
          <RequirePermission globalAnyOf={[PERMISSIONS.DATASET.ADD]}>
            <NewDataSet />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:id/edit',
        element: (
          <RequirePermission dataSetAccess>
            <EditDataSet />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:id/users',
        element: (
          <RequirePermission globalAnyOf={[PERMISSIONS.DATASET_ROLE.ASSIGN]}>
            <IndexDataSetUsers />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:id/integrations',
        element: (
          <RequirePermission dataSetAnyOf={[PERMISSIONS.INTEGRATION.VIEW]}>
            <IndexDataSetIntegrations />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:id/entities/:slug',
        element: (
          <RequirePermission dataSetAccess>
            <EntityRecordsPage />
          </RequirePermission>
        )
      },
      {
        path: '/service-accounts',
        element: (
          <RequirePermission globalAnyOf={[PERMISSIONS.SERVICE_ACCOUNT.VIEW]}>
            <ApiConnectionIndex />
          </RequirePermission>
        )
      },
      {
        path: '/users',
        element: (
          <RequirePermission globalAnyOf={[PERMISSIONS.USER.VIEW]}>
            <UsersIndex />
          </RequirePermission>
        )
      },
      {
        path: '/roles',
        element: (
          <RequirePermission globalAnyOf={[PERMISSIONS.GLOBAL_ROLE.VIEW, PERMISSIONS.DATASET_ROLE.VIEW, PERMISSIONS.GROUP.VIEW]}>
            <RolesIndex />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:dataSetId/agents',
        element: (
          <RequirePermission dataSetAnyOf={[PERMISSIONS.AGENT.VIEW]}>
            <AgentsPage />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:id/agentic-executions',
        element: (
          <RequirePermission
            dataSetAnyOf={[PERMISSIONS.AGENTIC_EXECUTION.CREATE, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL]}
          >
            <AgenticExecutionsPage />
          </RequirePermission>
        )
      },
      {
        path: '/data-sets/:id/agentic-executions/:executionId',
        element: (
          <RequirePermission
            dataSetAnyOf={[PERMISSIONS.AGENTIC_EXECUTION.CREATE, PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL]}
          >
            <AgenticExecutionDetailPage />
          </RequirePermission>
        )
      },
      {
        path: NO_DATA_SETS_PATH,
        element: <NoDataSets />
      },
      {
        path: '*',
        element: <NotFound />
      }
    ]
  },
  {
    path: "/login",
    element: <LoginPage />,
    loader: loginLoader
  },
  {
    path: "/onboarding",
    element: <OnboardingIndex />
  }
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
