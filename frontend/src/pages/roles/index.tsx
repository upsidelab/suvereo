import { useState } from "react";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { RolesTab, RolesTabs } from "@/components/roles/roles-tabs.tsx";
import { GroupsList } from "@/components/roles/groups/groups-list.tsx";
import { DatasetRolesList } from "@/components/roles/dataset-roles/dataset-roles-list.tsx";

export function RolesIndex() {
  const [activeTab, setActiveTab] = useState<RolesTab>("groups");

  return (
    <PageMain>
      <PageHeading title="Roles" description="Compose roles and manage groups." />
      <RolesTabs active={activeTab} onChange={setActiveTab} />
      {activeTab === "groups" && <GroupsList />}
      {activeTab === "dataset-roles" && <DatasetRolesList />}
    </PageMain>
  );
}
