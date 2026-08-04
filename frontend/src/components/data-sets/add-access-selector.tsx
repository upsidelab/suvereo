import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover.tsx";
import { Button } from "@/components/ui/button.tsx";
import { Check, ChevronsUpDown } from "lucide-react";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList
} from "@/components/ui/command.tsx";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select.tsx";
import { capitalize, cn } from "@/lib/utils.ts";
import { DatasetRoleOption, GroupOption, User } from "@/lib/types.ts";
import { useEffect, useState } from "react";

export interface AddAccessSelectorProps {
  availableUsers: User[];
  availableGroups: GroupOption[];
  availableRoles: DatasetRoleOption[];
  onSubmit: (targetType: "user" | "group", targetId: number, role: string) => void;
}

type Target = { type: "user"; id: number; label: string } | { type: "group"; id: number; label: string };

export function AddAccessSelector({ availableUsers, availableGroups, availableRoles, onSubmit }: AddAccessSelectorProps) {
  const [open, setOpen] = useState(false);
  const [selectedTarget, setSelectedTarget] = useState<Target | undefined>(undefined);
  const [role, setRole] = useState<string>(availableRoles[0]?.name ?? "");

  useEffect(() => {
    if (!role && availableRoles.length > 0) {
      setRole(availableRoles[0].name);
    }
  }, [availableRoles, role]);

  const targets: Target[] = [
    ...availableUsers.map((user) => ({ type: "user" as const, id: user.id, label: user.email })),
    ...availableGroups.map((group) => ({ type: "group" as const, id: group.id, label: capitalize(group.name) })),
  ];

  const handleSubmit = () => {
    if (!selectedTarget || !role) {
      return;
    }

    onSubmit(selectedTarget.type, selectedTarget.id, role);
    setSelectedTarget(undefined);
  };

  return (
    <div className="flex space-x-4">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-[400px] justify-between"
          >
            {selectedTarget
              ? `${selectedTarget.type === "user" ? "User" : "Group"}: ${selectedTarget.label}`
              : "Select user or group..."}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0">
          <Command>
            <CommandInput placeholder="Search..." />
            <CommandList>
              <CommandEmpty>No users or groups found.</CommandEmpty>
              <CommandGroup>
                {targets.map((target) => (
                  <CommandItem
                    key={`${target.type}-${target.id}`}
                    value={target.label}
                    onSelect={() => {
                      setSelectedTarget(target);
                      setOpen(false);
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedTarget?.type === target.type && selectedTarget?.id === target.id ? "opacity-100" : "opacity-0"
                      )}
                    />
                    {target.type === "user" ? "User" : "Group"}: {target.label}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      <Select value={role} onValueChange={setRole}>
        <SelectTrigger className="w-[140px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {availableRoles.map((roleOption) => (
            <SelectItem key={roleOption.id} value={roleOption.name}>
              {capitalize(roleOption.name)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button variant="default" onClick={handleSubmit} disabled={!selectedTarget || !role}>Add</Button>
    </div>
  )
}
