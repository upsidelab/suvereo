import { useState } from "react";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { RolesTab, RolesTabs } from "@/components/roles/roles-tabs.tsx";
import { GlobalRolesList } from "@/components/roles/global-roles/global-roles-list.tsx";
import { DatasetRolesList } from "@/components/roles/dataset-roles/dataset-roles-list.tsx";
import { GroupsList } from "@/components/roles/groups/groups-list.tsx";

export function RolesIndex() {
  const [activeTab, setActiveTab] = useState<RolesTab>("global-roles");

  return (
    <PageMain>
      <PageHeading
        title="Roles"
        description="Global roles apply everywhere; dataset roles are granted on individual data sets. Groups hold people, and are granted either kind."
      />
      <RolesTabs active={activeTab} onChange={setActiveTab} />
      {activeTab === "global-roles" && <GlobalRolesList />}
      {activeTab === "dataset-roles" && <DatasetRolesList />}
      {activeTab === "groups" && <GroupsList />}
    </PageMain>
  );
}
