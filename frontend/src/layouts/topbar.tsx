import { Menu, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { useTheme } from "@/hooks/use-theme";
import { CommandSearch } from "@/layouts/command-search";
import { NotificationsPopover } from "@/layouts/notifications-popover";
import { ProfileMenu } from "@/layouts/profile-menu";
import { BrandMark, SidebarNav } from "@/layouts/sidebar";

interface TopbarProps {
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
}

/** Top navigation: drawer trigger (mobile), search, theme, alerts, profile. */
export function Topbar({ sidebarCollapsed, onToggleSidebar }: TopbarProps) {
  const { resolvedTheme, setTheme } = useTheme();
  const [searchOpen, setSearchOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Global Ctrl/Cmd+K shortcut for search.
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-2 border-b bg-card px-3 sm:px-4">
      {/* Mobile drawer */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            aria-label="Open navigation"
          >
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="flex w-72 flex-col gap-0 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <BrandMark />
          <SidebarNav onNavigate={() => setDrawerOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Desktop sidebar collapse */}
      <Button
        variant="ghost"
        size="icon"
        className="hidden lg:inline-flex"
        onClick={onToggleSidebar}
        aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {sidebarCollapsed ? (
          <PanelLeftOpen className="h-4 w-4" />
        ) : (
          <PanelLeftClose className="h-4 w-4" />
        )}
      </Button>

      {/* Search */}
      <button
        type="button"
        onClick={() => setSearchOpen(true)}
        className="ml-1 flex h-9 flex-1 items-center gap-2 rounded-md border bg-background px-3 text-sm text-muted-foreground transition-colors hover:bg-accent sm:max-w-xs"
      >
        <Search className="h-4 w-4" />
        <span className="truncate">Search modules…</span>
        <kbd className="ml-auto hidden rounded border bg-muted px-1.5 py-0.5 text-[10px] font-medium sm:inline">
          Ctrl K
        </kbd>
      </button>
      <CommandSearch open={searchOpen} onOpenChange={setSearchOpen} />

      <div className="ml-auto flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          aria-label="Toggle dark mode"
        >
          {resolvedTheme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </Button>
        <NotificationsPopover />
        <ProfileMenu />
      </div>
    </header>
  );
}
