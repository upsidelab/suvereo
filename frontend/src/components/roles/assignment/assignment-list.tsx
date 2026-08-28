import { Button } from "@/components/ui/button.tsx";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table.tsx";
import { ScrollArea } from "@/components/ui/scroll-area.tsx";
import {
  AssignmentOption,
  assignmentKindLabel,
  assignmentOptionKey
} from "@/components/roles/assignment/assignment-option.ts";

export interface AssignmentListProps {
  items: AssignmentOption[];
  columnLabel: string;
  emptyMessage: string;
  removeLabel: string;
  onRemove?: (option: AssignmentOption) => void;
}

export function AssignmentList({ items, columnLabel, emptyMessage, removeLabel, onRemove }: AssignmentListProps) {
  const showsKind = items.some((item) => item.kind !== undefined);

  return (
    <ScrollArea className="grow min-h-0 w-full rounded-md border px-4 py-2">
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">{emptyMessage}</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              {showsKind && <TableHead className="whitespace-nowrap">Type</TableHead>}
              <TableHead className="w-full">{columnLabel}</TableHead>
              {onRemove && <TableHead className="whitespace-nowrap">Action</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => (
              <TableRow key={assignmentOptionKey(item)}>
                {showsKind && (
                  <TableCell className="whitespace-nowrap text-muted-foreground">
                    {item.kind ? assignmentKindLabel(item.kind) : ""}
                  </TableCell>
                )}
                <TableCell width="100%">
                  {item.label}
                  {item.note && <span className="ml-2 text-muted-foreground">{item.note}</span>}
                </TableCell>
                {onRemove && (
                  <TableCell className="whitespace-nowrap">
                    <Button variant="secondary" onClick={() => onRemove(item)}>{removeLabel}</Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </ScrollArea>
  );
}
