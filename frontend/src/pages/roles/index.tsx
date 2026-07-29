import { useState } from "react";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { RolesTab, RolesTabs } from "@/components/roles/roles-tabs.tsx";
import { GroupsList } from "@/components/roles/groups/groups-list.tsx";
import { GlobalRolesList } from "@/components/roles/global-roles/global-roles-list.tsx";

export function RolesIndex() {
  const [activeTab, setActiveTab] = useState<RolesTab>("global-roles");

  return (
    <PageMain>
      <PageHeading title="Roles" description="Compose global and dataset roles, and manage groups." />
      <RolesTabs active={activeTab} onChange={setActiveTab} />
      {activeTab === "global-roles" && <GlobalRolesList />}
      {activeTab === "dataset-roles" && <p className="text-muted-foreground">Coming in Task 10.</p>}
      {activeTab === "groups" && <GroupsList />}
    </PageMain>
  );
}
