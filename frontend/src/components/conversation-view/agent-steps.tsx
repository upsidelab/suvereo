import { useState } from "react";
import { CheckIcon, ChevronRightIcon } from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible.tsx";
import { cn } from "@/lib/utils.ts";

export type AgentStep =
  | { kind: "narration"; text: string }
  | { kind: "tool"; toolName: string; done: boolean };

interface AgentStepsProps {
  steps: AgentStep[];
}

const MAX_NAMED_TOOLS = 3;

const toolLabel = (toolName: string) => {
  const words = toolName.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
};

const summary = (steps: AgentStep[]) => {
  const names = [...new Set(steps.flatMap((step) => (step.kind === "tool" ? [toolLabel(step.toolName)] : [])))];
  const shown = names.slice(0, MAX_NAMED_TOOLS).join(", ");
  const more = names.length - MAX_NAMED_TOOLS;
  return more > 0 ? `Used ${shown} and ${more} more` : `Used ${shown}`;
};

export function AgentSteps({ steps }: AgentStepsProps) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="max-w-[75%] px-3 text-sm text-muted-foreground">
      <CollapsibleTrigger className="flex items-center gap-1.5 hover:text-foreground">
        <CheckIcon className="h-3.5 w-3.5" />
        <span>{summary(steps)}</span>
        <ChevronRightIcon className={cn("h-3.5 w-3.5 transition-transform", open && "rotate-90")} />
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-2 ml-1.5 space-y-2 border-l pl-3">
        {steps.map((step, index) =>
          step.kind === "narration" ? (
            <p key={index}>{step.text}</p>
          ) : (
            <p key={index}>{toolLabel(step.toolName)}</p>
          )
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
