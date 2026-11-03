import { useEffect, useState } from "react";
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader } from "@/components/ui/sidebar.tsx";
import { DataSetSelector } from "@/components/navigation/data-set-selector.tsx";
import { MainSidebarSection, SidebarSectionItemProps } from "@/components/navigation/main-sidebar-section.tsx";
import {
  BookTextIcon,
  BotMessageSquareIcon,
  DatabaseIcon,
  HelpCircleIcon,
  HistoryIcon,
  LayersIcon,
  LinkIcon,
  PlayIcon,
  PlugZapIcon,
  Settings2Icon,
  ShieldIcon,
  SparklesIcon,
  UserIcon,
} from "lucide-react";
import { UserMenu } from "@/components/navigation/user-menu.tsx";
import { useApplicationContext } from "@/lib/use-application-context.ts";
import { ApiClient } from "@/lib/api.ts";
import { authenticationProviderInstance } from "@/lib/authentication-provider.ts";
import { EntityType } from "@/lib/types.ts";
import { PERMISSIONS } from "@/lib/permissions/codes.ts";

const api = new ApiClient(authenticationProviderInstance);

export function MainSidebar() {
  const { account, dataSetId, dataSets, isLoadingAgents, availableAgents, hasPermission, hasDataSetPermission } = useApplicationContext()!;
  const canViewAgents = hasDataSetPermission(PERMISSIONS.AGENT.VIEW);
  const canAddAgents = hasDataSetPermission(PERMISSIONS.AGENT.ADD);
  const canViewIntegrations = hasDataSetPermission(PERMISSIONS.INTEGRATION.VIEW);
  const canUseExecutions = hasDataSetPermission(PERMISSIONS.AGENTIC_EXECUTION.CREATE)
    || hasDataSetPermission(PERMISSIONS.AGENTIC_EXECUTION.VIEW_ALL);
  const canConverse = hasDataSetPermission(PERMISSIONS.CONVERSATION.CONVERSE);
  const canViewAllConversations = hasDataSetPermission(PERMISSIONS.CONVERSATION.VIEW_ALL);
  const canSeeAsk = canConverse || canViewAllConversations;
  const [entityTypes, setEntityTypes] = useState<EntityType[]>([]);
  const hasDataSetAccess = dataSets.length > 0;

  useEffect(() => {
    if (!hasDataSetAccess) {
      setEntityTypes([]);
      return;
    }

    api.entities().listTypes().then(setEntityTypes).catch(() => setEntityTypes([]));
  }, [hasDataSetAccess]);

  const converseItems: SidebarSectionItemProps[] = canConverse ? [
    ...(isLoadingAgents ? [] : availableAgents.map(agent => ({
      title: agent.name,
      link: `/data-sets/${dataSetId}/chat/new/${encodeURIComponent(agent.id)}`,
      key: agent.id.toString(),
      icon: <BotMessageSquareIcon />
    }))),
    ...(isLoadingAgents || availableAgents.length > 0 ? [] : [
      {
        title: "No Agents configured",
        link: `/data-sets/${dataSetId}/agents?action=add`,
        key: "no-agents-configured",
        icon: <BotMessageSquareIcon />,
        disabled: true
      },
      ...(canAddAgents ? [{
        title: "Add Agent",
        link: `/data-sets/${dataSetId}/agents?action=add`,
        key: "configure-agent",
        icon: <Settings2Icon />
      }] : [])
    ])
  ] : [];

  const askItems: SidebarSectionItemProps[] = [
    ...converseItems,
    {
      title: "History",
      link: `/data-sets/${dataSetId}/history`,
      key: "history",
      icon: <HistoryIcon />
    }
  ];

  const canSeeDataSets = dataSets.length > 0 || hasPermission(PERMISSIONS.DATA_SET.ADD);
  const canSeeUsers = hasPermission(PERMISSIONS.USER.VIEW);
  const canSeeServiceAccounts = hasPermission(PERMISSIONS.SERVICE_ACCOUNT.VIEW);
  const canSeeRoles = hasPermission(PERMISSIONS.GLOBAL_ROLE.VIEW)
    || hasPermission(PERMISSIONS.DATA_SET_ROLE.VIEW)
    || hasPermission(PERMISSIONS.GROUP.VIEW);
  const hasManageAccess = canSeeDataSets || canSeeUsers || canSeeServiceAccounts || canSeeRoles;

  const manageItems: SidebarSectionItemProps[] = [
    ...(canSeeDataSets ? [{
      title: "Data Sets",
      link: "/data-sets",
      key: "data-sets",
      icon: <DatabaseIcon />
    }] : []),
    ...(canSeeUsers ? [{
      title: "Users",
      link: "/users",
      key: "users",
      icon: <UserIcon />
    }] : []),
    ...(canSeeServiceAccounts ? [{
      title: "Service Accounts",
      link: "/service-accounts",
      key: "service-accounts",
      icon: <PlugZapIcon />
    }] : []),
    ...(canSeeRoles ? [{
      title: "Roles",
      link: "/roles",
      key: "roles",
      icon: <ShieldIcon />
    }] : []),
  ];

  const helpItems: SidebarSectionItemProps[] = [
    {
      title: "Help",
      link: "https://upsidelab.io/tools/enthusiast/docs",
      key: "help",
      icon: <HelpCircleIcon />,
      children: [
        {
          title: "Getting Started",
          link: "https://upsidelab.io/tools/enthusiast/docs/getting-started/import-test-data",
          key: "documentation-getting-started",
          icon: <SparklesIcon />,
          external: true
        },
        {
          title: "API Documentation",
          link: `${import.meta.env.VITE_API_BASE}/api/docs`,
          key: "api-documentation",
          icon: <BookTextIcon />,
          external: true
        }
      ]
    },
  ];

  const configureItems: SidebarSectionItemProps[] = [
    ...(canViewAgents ? [{
      title: "Agents",
      link: `/data-sets/${dataSetId}/agents`,
      key: "agents",
      icon: <BotMessageSquareIcon />
    }] : []),
    ...(canUseExecutions ? [{
      title: "Agentic Executions",
      link: `/data-sets/${dataSetId}/agentic-executions`,
      key: "agentic-executions",
      icon: <PlayIcon />
    }] : []),
    ...(canViewIntegrations ? [{
      title: "Integrations",
      link: `/data-sets/${dataSetId}/integrations`,
      key: "integrations",
      icon: <LinkIcon />
    }] : []),
  ];

  const catalogItems: SidebarSectionItemProps[] = entityTypes.map(entityType => ({
    title: entityType.label,
    link: `/data-sets/${dataSetId}/entities/${entityType.slug}`,
    key: `entity-${entityType.slug}`,
    icon: <LayersIcon />
  }));

  return (
    <Sidebar>
      <SidebarHeader>
        <DataSetSelector />
      </SidebarHeader>
      <SidebarContent>
        {dataSetId !== null && (
          <>
            {canSeeAsk && (
              <MainSidebarSection title="Ask" items={askItems} />
            )}
            {configureItems.length > 0 && (
              <MainSidebarSection title="Configure" items={configureItems} />
            )}
            {catalogItems.length > 0 && (
              <MainSidebarSection title="Catalog" items={catalogItems} />
            )}
          </>
        )}
        <div className="mt-auto">
          {account && hasManageAccess && (
            <MainSidebarSection title="Manage" items={manageItems} />
          )}
          <MainSidebarSection items={helpItems} />
        </div>
      </SidebarContent>
      <SidebarFooter>
        <UserMenu />
      </SidebarFooter>
    </Sidebar>
  );
}
