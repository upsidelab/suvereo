import { ReactNode, useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

// Scrolling one axis makes the other clip too, cutting the focus ring off the sides of an input.
// The padding gives it room; the negative margin keeps fields aligned with the Save button outside.
const RING_ROOM = "px-1 -mx-1 py-1";

export interface ModalScrollAreaProps {
  className?: string;
  children: ReactNode;
}

export function ModalScrollArea({ className, children }: ModalScrollAreaProps) {
  const viewport = useRef<HTMLDivElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const [showFade, setShowFade] = useState(false);

  useEffect(() => {
    const element = viewport.current;
    if (!element) return;

    const update = () => {
      setShowFade(element.scrollHeight - element.clientHeight - element.scrollTop > 1);
    };

    // The viewport keeps its size while the content grows, so a dragged textarea only ever
    // resizes the content - observing the viewport alone would miss it.
    const observer = new ResizeObserver(update);
    observer.observe(element);
    if (content.current) observer.observe(content.current);
    element.addEventListener("scroll", update);
    update();

    return () => {
      observer.disconnect();
      element.removeEventListener("scroll", update);
    };
  }, []);

  return (
    <div className="relative grow min-h-0">
      <div
        ref={viewport}
        className={cn("h-full overflow-y-auto [&::-webkit-scrollbar]:hidden", RING_ROOM)}
        style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
      >
        <div ref={content} className={className}>{children}</div>
      </div>
      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 bottom-0 h-6 transition-opacity",
          "bg-gradient-to-t from-background to-transparent",
          showFade ? "opacity-100" : "opacity-0"
        )}
      />
    </div>
  );
}
