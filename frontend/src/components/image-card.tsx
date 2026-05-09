"use client";

import { useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";

interface ImageCardProps {
  src: string;
  alt: string;
  width: number;
  height: number;
  index: number;
  onClick: () => void;
}

export function ImageCard({ src, alt, width, height, index, onClick }: ImageCardProps) {
  const [loaded, setLoaded] = useState(false);

  return (
    <div
      className="group relative overflow-hidden bg-muted break-inside-avoid cursor-pointer"
      onClick={onClick}
    >
      {!loaded && (
        <Skeleton className="absolute inset-0 h-full w-full" />
      )}
      <img
        src={src}
        alt={alt}
        loading="lazy"
        onLoad={() => setLoaded(true)}
        className={`w-full object-cover transition-all duration-500 ease-out ${
          loaded ? "opacity-100 scale-100" : "opacity-0 scale-105"
        } group-hover:scale-105`}
        style={{
          aspectRatio: `${width} / ${height}`,
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
      <div className="absolute bottom-0 left-0 right-0 p-3 opacity-0 transition-opacity duration-300 group-hover:opacity-100">
        <p className="truncate text-sm font-medium text-white">{alt}</p>
      </div>
    </div>
  );
}
