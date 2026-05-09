"use client";

import { ThemeToggle } from "./theme-toggle";
import { Input } from "@/components/ui/input";
import { Search, X, Menu } from "lucide-react";
import { Button } from "@/components/ui/button";

interface TopNavbarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  sidebarOpen: boolean;
  onToggleSidebar: () => void;
}

export function TopNavbar({
  searchQuery,
  onSearchChange,
  sidebarOpen,
  onToggleSidebar,
}: TopNavbarProps) {
  return (
    <header className="sticky top-0 z-50 flex h-16 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <Button
        variant="ghost"
        size="icon"
        className="h-9 w-9 shrink-0"
        onClick={onToggleSidebar}
      >
        {sidebarOpen ? (
          <X className="h-[1.2rem] w-[1.2rem]" />
        ) : (
          <Menu className="h-[1.2rem] w-[1.2rem]" />
        )}
      </Button>

      <div className="flex flex-1 items-center justify-center px-4">
        <div className="relative w-full max-w-xl">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search photos..."
            className="h-10 w-full rounded-lg border-border bg-background pl-10 pr-4 text-sm"
          />
        </div>
      </div>

      <ThemeToggle />
    </header>
  );
}
