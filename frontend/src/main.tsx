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
import { PERMISSIONS } from "@/lib/permissions.ts";

const api = new ApiClient(authenticationProviderInstance);

const GLOBAL_MANAGE_ROUTES = [
  { path: "/users", permissions: [PERMISSIONS.USER.VIEW] },
  { path: "/service-accounts", permissions: [PERMISSIONS.SERVICE_ACCOUNT.VIEW] },
  { path: "/roles", permissions: [PERMISSIONS.GROUP.VIEW, PERMISSIONS.DATASET_ROLE.VIEW] },
];

const requireAnyPermission = (permissions: string[]) => async () => {
  const accountData = await api.getAccount();
  if (!permissions.some(permission => accountData.permissions.includes(permission))) {
    return redirect("/");
  }
  return null;
};

const protectedLoginLoader = async ({ request }: LoaderFunctionArgs) => {
  if (!authenticationProviderInstance.isAuthenticated()) {
    return redirect("/login");
  }

  const apiDataSets = await api.dataSets().getDataSets();
  if (!apiDataSets) {
    return redirect("/login");
  }

  if (apiDataSets.length === 0) {
    const accountData = await api.getAccount();
    if (accountData.permissions.includes(PERMISSIONS.DATASET.ADD)) {
      return redirect("/onboarding");
    }

    const manageRoutes = GLOBAL_MANAGE_ROUTES.filter(
      route => route.permissions.some(permission => accountData.permissions.includes(permission))
    );
    if (manageRoutes.length === 0) {
      return redirect("/no-data-sets");
    }

    const { pathname } = new URL(request.url);
    if (!manageRoutes.some(route => pathname.startsWith(route.path))) {
      return redirect(manageRoutes[0].path);
    }
  }

  return null;
};

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    loader: protectedLoginLoader,
    errorElement: <ErrorPage />,
    children: [
      {
        path: "/",
        element: <Chat />
      },
      {
        path: '/data-sets/:id/chat',
        element: <Chat />,
        children: [
          { path: 'new' },
          { path: 'new/:agent' },
          { path: ':chatId' }
        ]
      },
      {
        path: '/data-sets/:id/history',
        element: <ChatHistory />
      },
      {
        path: '/data-sets',
        element: <DataSetsIndex />
      },
      {
        path: '/data-sets/new',
        element: <NewDataSet />
      },
      {
        path: '/data-sets/:id/edit',
        element: <EditDataSet />
      },
      {
        path: '/data-sets/:id/users',
        element: <IndexDataSetUsers />
      },
      {
        path: '/data-sets/:id/integrations',
        element: <IndexDataSetIntegrations />
      },
      {
        path: '/data-sets/:id/entities/:slug',
        element: <EntityRecordsPage />
      },
      {
        path: '/service-accounts',
        element: <ApiConnectionIndex />
      },
      {
        path: '/users',
        element: <UsersIndex />
      },
      {
        path: '/roles',
        element: <RolesIndex />,
        loader: requireAnyPermission([PERMISSIONS.GROUP.VIEW, PERMISSIONS.DATASET_ROLE.VIEW])
      },
      {
        path: '/data-sets/:dataSetId/agents',
        element: <AgentsPage />
      },
      {
        path: '/data-sets/:id/agentic-executions',
        element: <AgenticExecutionsPage />
      },
      {
        path: '/data-sets/:id/agentic-executions/:executionId',
        element: <AgenticExecutionDetailPage />
      }
    ]
  },
  {
    path: "/login",
    element: <LoginPage />
  },
  {
    path: "/no-data-sets",
    element: <NoDataSets />
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
