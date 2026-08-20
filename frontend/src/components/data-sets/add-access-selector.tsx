import { useEffect, useState } from "react";
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
import { cn } from "@/lib/utils.ts";
import { DatasetRoleOption } from "@/lib/types.ts";
import { AccessRow, AccessSubject } from "@/components/data-sets/access-row.ts";

export interface AddAccessSelectorProps {
  subjects: AccessSubject[];
  roles: DatasetRoleOption[];
  grantedRoles: AccessRow[];
  onSubmit: (subject: AccessSubject, roleId: number) => void;
}

export function AddAccessSelector({ subjects, roles, grantedRoles, onSubmit }: AddAccessSelectorProps) {
  const [open, setOpen] = useState(false);
  const [selectedSubject, setSelectedSubject] = useState<AccessSubject | undefined>(undefined);
  const [selectedRoleId, setSelectedRoleId] = useState<number | undefined>(roles[0]?.id);

  useEffect(() => {
    if (selectedRoleId === undefined && roles.length > 0) {
      setSelectedRoleId(roles[0].id);
    }
  }, [roles, selectedRoleId]);

  const alreadyHoldsSelectedRole = (subject: AccessSubject) => grantedRoles.some((row) =>
    row.subject.type === subject.type && row.subject.id === subject.id && row.role.id === selectedRoleId);

  const selectableSubjects = subjects.filter((subject) => !alreadyHoldsSelectedRole(subject));
  const canSubmit = selectedSubject !== undefined
    && selectedRoleId !== undefined
    && !alreadyHoldsSelectedRole(selectedSubject);

  const handleSubmit = () => {
    if (!selectedSubject || selectedRoleId === undefined) return;
    onSubmit(selectedSubject, selectedRoleId);
    setSelectedSubject(undefined);
  };

  return (
    <div className="flex space-x-4">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" role="combobox" aria-expanded={open} className="w-[400px] justify-between">
            {selectedSubject ? `${subjectTypeLabel(selectedSubject)}: ${selectedSubject.label}` : "Select user or global role..."}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0">
          <Command>
            <CommandInput placeholder="Search..." />
            <CommandList>
              <CommandEmpty>No users or global roles found.</CommandEmpty>
              <CommandGroup>
                {selectableSubjects.map((subject) => (
                  <CommandItem
                    key={`${subject.type}-${subject.id}`}
                    value={subject.label}
                    onSelect={() => {
                      setSelectedSubject(subject);
                      setOpen(false);
                    }}
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        selectedSubject?.type === subject.type && selectedSubject?.id === subject.id
                          ? "opacity-100"
                          : "opacity-0"
                      )}
                    />
                    {subjectTypeLabel(subject)}: {subject.label}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      <Select
        value={selectedRoleId === undefined ? "" : String(selectedRoleId)}
        onValueChange={(value) => setSelectedRoleId(Number(value))}
      >
        <SelectTrigger className="w-[200px]">
          <SelectValue placeholder="Select a role..." />
        </SelectTrigger>
        <SelectContent>
          {roles.map((role) => (
            <SelectItem key={role.id} value={String(role.id)}>{role.name}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button variant="default" onClick={handleSubmit} disabled={!canSubmit}>Add</Button>
    </div>
  );
}

function subjectTypeLabel(subject: AccessSubject): string {
  return subject.type === "user" ? "User" : "Global role";
}
