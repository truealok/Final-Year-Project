import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { NAV_ITEMS } from "@/layouts/nav-items";
import { cn } from "@/lib/utils";

interface CommandSearchProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** Lightweight module search (Ctrl/Cmd+K) that jumps to any page. */
export function CommandSearch({ open, onOpenChange }: CommandSearchProps) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const navigate = useNavigate();

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return NAV_ITEMS;
    return NAV_ITEMS.filter((item) => item.label.toLowerCase().includes(q));
  }, [query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, open]);

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const go = (to: string) => {
    onOpenChange(false);
    navigate(to);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="top-[20%] max-w-md translate-y-0 gap-0 p-0">
        <DialogTitle className="sr-only">Search modules</DialogTitle>
        <DialogDescription className="sr-only">
          Type to filter modules, Enter to open.
        </DialogDescription>
        <div className="relative border-b">
          <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "ArrowDown") {
                event.preventDefault();
                setActiveIndex((i) => Math.min(i + 1, results.length - 1));
              } else if (event.key === "ArrowUp") {
                event.preventDefault();
                setActiveIndex((i) => Math.max(i - 1, 0));
              } else if (event.key === "Enter" && results[activeIndex]) {
                go(results[activeIndex].to);
              }
            }}
            placeholder="Search modules…"
            className="h-12 border-0 pl-10 shadow-none focus-visible:ring-0"
          />
        </div>
        <ul className="max-h-72 overflow-y-auto p-2">
          {results.length === 0 && (
            <li className="px-3 py-6 text-center text-sm text-muted-foreground">
              No modules match “{query}”.
            </li>
          )}
          {results.map(({ to, label, icon: Icon }, index) => (
            <li key={to}>
              <button
                type="button"
                onClick={() => go(to)}
                onMouseEnter={() => setActiveIndex(index)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm",
                  index === activeIndex
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground",
                )}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
