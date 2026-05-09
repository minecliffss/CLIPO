"use client";

import { useEffect, useState, useMemo } from "react";
import { TopNavbar } from "@/components/top-navbar";
import { LeftSidebar } from "@/components/left-sidebar";
import { ImageCard } from "@/components/image-card";
import { ImageLightbox } from "@/components/image-lightbox";
import { Skeleton } from "@/components/ui/skeleton";

interface ImageItem {
  name: string;
  src: string;
  alt: string;
  width: number;
  height: number;
  score?: number;
}

const API_BASE = "http://localhost:3001";

export default function Home() {
  const [images, setImages] = useState<ImageItem[]>([]);
  const [aiResults, setAiResults] = useState<ImageItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  // Load all images on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/images`)
      .then((res) => res.json())
      .then((data) => {
        setImages(data.images || []);
        setLoading(false);
      })
      .catch(() => {
        // Fallback to local images.json if backend is down
        fetch("/images.json")
          .then((res) => res.json())
          .then((data) => {
            setImages(data.images || []);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  }, []);

  // Debounced AI Search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setAiResults(null);
      setSearching(false);
      return;
    }

    setSearching(true);
    const timer = setTimeout(() => {
      fetch(`${API_BASE}/api/search?q=${encodeURIComponent(searchQuery)}`)
        .then((res) => res.json())
        .then((data) => {
          setAiResults(data.images || []);
          setSearching(false);
        })
        .catch((err) => {
          console.error("AI Search failed:", err);
          setAiResults([]); // Show no results on error
          setSearching(false);
        });
    }, 500);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Combine AI results and local images
  const filteredImages = useMemo(() => {
    if (aiResults !== null) return aiResults;
    if (!searchQuery.trim()) return images;
    
    // Fallback: simple text search if AI results didn't load yet
    const q = searchQuery.toLowerCase();
    return images.filter(
      (img) =>
        img.alt.toLowerCase().includes(q) ||
        img.name.toLowerCase().includes(q)
    );
  }, [images, aiResults, searchQuery]);

  const openLightbox = (index: number) => {
    setLightboxIndex(index);
    setLightboxOpen(true);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <TopNavbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        sidebarOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />

      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar
          activeFilter={activeFilter}
          onFilterChange={setActiveFilter}
          open={sidebarOpen}
        />

        <main className="flex-1 overflow-auto px-4 py-6 md:px-6">
          <div className="mx-auto max-w-7xl">
            <div className="mb-6">
              <h1 className="text-2xl font-bold tracking-tight">
                {searchQuery.trim() ? "AI Search Results" : "All Photos"}
              </h1>
              <p className="text-muted-foreground mt-1">
                {loading || searching
                  ? "Searching..."
                  : `${filteredImages.length} images found`}
              </p>
            </div>

            {loading ? (
              <div className="columns-2 gap-0 sm:columns-3 md:columns-4 lg:columns-5 xl:columns-6">
                {Array.from({ length: 18 }).map((_, i) => (
                  <Skeleton
                    key={i}
                    className="mb-0 aspect-[3/4] break-inside-avoid"
                  />
                ))}
              </div>
            ) : (
              <div className="columns-2 gap-0 sm:columns-3 md:columns-4 lg:columns-5 xl:columns-6">
                {filteredImages.map((image, index) => (
                  <ImageCard
                    key={`${image.name}-${index}`}
                    src={image.src.startsWith("http") ? image.src : `${API_BASE}${image.src}`}
                    alt={image.alt}
                    width={image.width}
                    height={image.height}
                    index={index}
                    onClick={() => openLightbox(index)}
                  />
                ))}
              </div>
            )}
          </div>
        </main>
      </div>

      <ImageLightbox
        images={filteredImages}
        currentIndex={lightboxIndex}
        isOpen={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        onPrev={() => setLightboxIndex((i) => Math.max(0, i - 1))}
        onNext={() =>
          setLightboxIndex((i) => Math.min(filteredImages.length - 1, i + 1))
        }
      />
    </div>
  );
}
