import * as React from "react"
import { CheckIcon, ChevronDownIcon } from "@radix-ui/react-icons"

import { cn } from "@/lib/utils"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"

interface SearchableSelectProps {
  value?: string
  onChange: (value: string) => void
  options?: string[]
  placeholder?: string
  searchPlaceholder?: string
  emptyText?: string
  disabled?: boolean
}

export function SearchableSelect({
  value,
  onChange,
  options = [],
  placeholder,
  searchPlaceholder = "Search...",
  emptyText = "No results found.",
  disabled,
}: SearchableSelectProps) {
  const [open, setOpen] = React.useState(false)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        <button
          type="button"
          role="combobox"
          aria-expanded={open}
          className="flex h-9 w-full items-center justify-between whitespace-nowrap rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm ring-offset-background focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className={cn("line-clamp-1 text-left", !value && "text-muted-foreground")}>{value || placeholder}</span>
          <ChevronDownIcon className="h-4 w-4 shrink-0 opacity-50" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command>
          <CommandInput placeholder={searchPlaceholder} />
          <CommandList>
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {options.map((option) => (
                <CommandItem
                  key={option}
                  value={option}
                  onSelect={() => {
                    onChange(option)
                    setOpen(false)
                  }}
                >
                  {option}
                  <CheckIcon className={cn("ml-auto h-4 w-4", option === value ? "opacity-100" : "opacity-0")} />
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
