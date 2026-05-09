"use client";

import { ImageIcon, FolderOpen, Heart, Clock, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LeftSidebarProps {
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  open: boolean;
}

const filters = [
  { icon: ImageIcon, label: "All Photos", id: "all" },
  { icon: FolderOpen, label: "Albums", id: "albums" },
  { icon: Heart, label: "Favorites", id: "favorites" },
  { icon: Clock, label: "Recent", id: "recent" },
  { icon: Trash2, label: "Trash", id: "trash" },
];

export function LeftSidebar({ activeFilter, onFilterChange, open }: LeftSidebarProps) {
  if (!open) return null;

  return (
    <aside className="w-56 shrink-0 flex-col border-r border-border bg-background flex">
      <div className="flex flex-col gap-1 p-3">
        {filters.map((item) => (
          <button
            key={item.id}
            onClick={() => onFilterChange(item.id)}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
              activeFilter === item.id
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <item.icon className="h-4 w-4" />
            {item.label}
          </button>
        ))}
      </div>
    </aside>
  );
}
