import { Button } from "@/components/ui/button.tsx";

export interface ModalSection<T extends string> {
  key: T;
  label: string;
}

export interface ModalSectionsProps<T extends string> {
  sections: readonly ModalSection<T>[];
  active: T;
  onChange: (section: T) => void;
}

export function ModalSections<T extends string>({ sections, active, onChange }: ModalSectionsProps<T>) {
  return (
    <div className="flex items-center space-x-2 border-b pb-2">
      {sections.map((section) => (
        <Button
          key={section.key}
          type="button"
          variant={active === section.key ? "default" : "ghost"}
          onClick={() => onChange(section.key)}
        >
          {section.label}
        </Button>
      ))}
    </div>
  );
}
