import { ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { DEFAULT_ROLES_TAB, RolesTab, RolesTabs, TAB_PARAM } from "@/components/roles/roles-tabs.tsx";
import { GlobalRolesList } from "@/components/roles/global-roles/global-roles-list.tsx";
import { DataSetRolesList } from "@/components/roles/data-set-roles/data-set-roles-list.tsx";
import { GroupsList } from "@/components/roles/groups/groups-list.tsx";

// Typed against RolesTab, so adding a tab to the union will not compile until its content is here.
const TAB_CONTENT: Record<RolesTab, ReactNode> = {
  "global-roles": <GlobalRolesList />,
  "data-set-roles": <DataSetRolesList />,
  "groups": <GroupsList />,
};

function isRolesTab(value: string | null): value is RolesTab {
  return value !== null && value in TAB_CONTENT;
}

export function RolesIndex() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedTab = searchParams.get(TAB_PARAM);
  const activeTab = isRolesTab(requestedTab) ? requestedTab : DEFAULT_ROLES_TAB;

  const selectTab = (tab: RolesTab) => {
    setSearchParams(prev => {
      const next = new URLSearchParams(prev);
      if (tab === DEFAULT_ROLES_TAB) next.delete(TAB_PARAM);
      else next.set(TAB_PARAM, tab);
      return next;
    });
  };

  return (
    <PageMain>
      <PageHeading
        title="Roles"
        description={"Define roles — global, or scoped to a data set. Assign users and service accounts to them "
          + "directly, or through groups."}
      />
      <RolesTabs active={activeTab} onChange={selectTab} />
      {TAB_CONTENT[activeTab]}
    </PageMain>
  );
}
