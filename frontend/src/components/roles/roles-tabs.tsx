import { Button } from "@/components/ui/button.tsx";

export type RolesTab = "global-roles" | "dataset-roles" | "groups";

const TABS: { key: RolesTab; label: string; description: string }[] = [
  {
    key: "global-roles",
    label: "Global Roles",
    description: "A global role carries permissions that apply everywhere, across every data set. Grant one to a "
      + "user or service account directly, or to a group so that everyone inside it holds it."
  },
  {
    key: "dataset-roles",
    label: "Dataset Roles",
    description: "A dataset role carries permissions that apply only on the data sets it is granted on. Grant it "
      + "to a user or service account directly, or to a group, separately on each data set."
  },
  {
    key: "groups",
    label: "Groups",
    description: "A group holds users and service accounts, and no permissions of its own. Grant it a global "
      + "role or a dataset role and every member holds it — add someone later and they hold it too."
  },
];

export interface RolesTabsProps {
  active: RolesTab;
  onChange: (tab: RolesTab) => void;
}

export function RolesTabs({ active, onChange }: RolesTabsProps) {
  const activeDescription = TABS.find((tab) => tab.key === active)?.description;

  return (
    <div className="mb-6">
      <div className="flex space-x-2 border-b pb-2">
        {TABS.map((tab) => (
          <Button
            key={tab.key}
            variant={active === tab.key ? "default" : "ghost"}
            onClick={() => onChange(tab.key)}
          >
            {tab.label}
          </Button>
        ))}
      </div>
      <p className="text-sm text-muted-foreground mt-4">{activeDescription}</p>
    </div>
  );
}
