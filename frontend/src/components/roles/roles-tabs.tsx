import { Button } from "@/components/ui/button.tsx";

export type RolesTab = "global-roles" | "dataset-roles";

const TABS: { key: RolesTab; label: string }[] = [
  { key: "global-roles", label: "Global Roles" },
  { key: "dataset-roles", label: "Dataset Roles" },
];

export interface RolesTabsProps {
  active: RolesTab;
  onChange: (tab: RolesTab) => void;
}

export function RolesTabs({ active, onChange }: RolesTabsProps) {
  return (
    <div className="flex space-x-2 mb-6 border-b pb-2">
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
  );
}
