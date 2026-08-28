import { Fragment, useEffect, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button.tsx";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible.tsx";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog.tsx";
import { EscalationRisk, PermissionEntity } from "@/lib/permissions/types.ts";
import { PermissionLabel } from "@/components/roles/permission-label.tsx";

export interface PermissionEscalationDialogProps {
  open: boolean;
  risks: EscalationRisk[];
  entities: PermissionEntity[];
  onConfirm: () => void;
  onCancel: () => void;
}

export function PermissionEscalationDialog({
  open,
  risks,
  entities,
  onConfirm,
  onCancel,
}: PermissionEscalationDialogProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    if (!open) setDetailsOpen(false);
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Confirm granting these sensitive permissions</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <p className="text-sm text-destructive">
            {risks.map((risk, index) => (
              <Fragment key={risk.code}>
                {index > 0 && ", "}
                <PermissionLabel code={risk.code} entities={entities} />
              </Fragment>
            ))}
          </p>
          <p className="text-sm">
            Holders of those permissions can widen access beyond what you grant here, including
            their own.
          </p>
          <p className="text-sm">
            Continue only if that is intended.
          </p>

          <Collapsible open={detailsOpen} onOpenChange={setDetailsOpen} className="py-3">
            <CollapsibleTrigger asChild>
              <Button variant="ghost" className="h-auto p-0 font-normal text-muted-foreground">
                {detailsOpen ? <ChevronDown className="mr-1 h-4 w-4" /> : <ChevronRight className="mr-1 h-4 w-4" />}
                Details
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="mt-2">
              <ul className="space-y-2 border-l pl-4">
                {risks.map((risk) => (
                  <li key={risk.code} className="text-sm">
                    <PermissionLabel code={risk.code} entities={entities} />
                    <span className="text-muted-foreground"> — {risk.detail}</span>
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        </div>

        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onCancel}>Cancel</Button>
          <Button onClick={onConfirm}>Save anyway</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
