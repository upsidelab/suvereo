import { useState } from "react";
import { PageHeading } from "@/components/util/page-heading.tsx";
import { PageMain } from "@/components/util/page-main.tsx";
import { RolesTab, RolesTabs } from "@/components/roles/roles-tabs.tsx";
import { GlobalRolesList } from "@/components/roles/global-roles/global-roles-list.tsx";
import { DataSetRolesList } from "@/components/roles/data-set-roles/data-set-roles-list.tsx";
import { GroupsList } from "@/components/roles/groups/groups-list.tsx";

export function RolesIndex() {
  const [activeTab, setActiveTab] = useState<RolesTab>("global-roles");

  return (
    <PageMain>
      <PageHeading
        title="Roles"
        description={"Define roles — global, or scoped to a data set. Assign users and service accounts to them "
          + "directly, or through groups."}
      />
      <RolesTabs active={activeTab} onChange={setActiveTab} />
      {activeTab === "global-roles" && <GlobalRolesList />}
      {activeTab === "data-set-roles" && <DataSetRolesList />}
      {activeTab === "groups" && <GroupsList />}
    </PageMain>
  );
}
