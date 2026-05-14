"use client";

import { useEffect, useState, useMemo } from "react";
import { TopNavbar } from "@/components/top-navbar";
import { LeftSidebar } from "@/components/left-sidebar";
import { ImageCard } from "@/components/image-card";
import { ImageLightbox } from "@/components/image-lightbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

interface ImageItem {
  name: string;
  src: string;
  alt: string;
  width: number;
  height: number;
  score?: number;
}

const API_BASE = "http://localhost:3001";

function FolderOnboarding({ onFolderSelect }: { onFolderSelect: (folder: string) => void }) {
  const [folderPath, setFolderPath] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!folderPath.trim()) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/folder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ folder: folderPath }),
      });
      const data = await res.json();
      if (data.success) {
        onFolderSelect(folderPath);
      } else {
        alert(data.message);
      }
    } catch (err) {
      alert("Failed to set folder");
    }
    setLoading(false);
  };

  const handleQuickFolder = (path: string) => {
    setFolderPath(path);
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="max-w-md w-full text-center space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Welcome to CLIPO</h1>
          <p className="text-muted-foreground mt-2">AI-powered photo search for your gallery</p>
        </div>

        <div className="rounded-lg border bg-card p-6 text-left">
          <h2 className="text-lg font-semibold mb-4">Select your photo folder</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Choose the folder containing your photos. The AI will index them for semantic search.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="/home/daniel/Pictures"
              className="w-full px-3 py-2 border rounded-md bg-background"
            />
            <Button type="submit" className="w-full" disabled={loading || !folderPath.trim()}>
              {loading ? "Indexing..." : "Start Indexing"}
            </Button>
          </form>
        </div>

        <div>
          <p className="text-sm text-muted-foreground mb-2">Quick select:</p>
          <div className="flex flex-wrap justify-center gap-2">
            {["~/Pictures", "~/Desktop/Images", "~/Images", "~/Photos"].map((p) => (
              <button
                key={p}
                onClick={() => handleQuickFolder(p)}
                className="text-sm px-3 py-1 rounded-full border hover:bg-accent"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

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
  const [folderConfigured, setFolderConfigured] = useState<boolean | null>(null);

  // Check folder configuration
  useEffect(() => {
    fetch(`${API_BASE}/api/folder`)
      .then((res) => res.json())
      .then((data) => {
        setFolderConfigured(!!data.folder);
        if (data.folder) {
          loadImages();
        } else {
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
  }, []);

  const loadImages = () => {
    fetch(`${API_BASE}/api/images`)
      .then((res) => res.json())
      .then((data) => {
        setImages(data.images || []);
        setLoading(false);
      })
      .catch(() => {
        fetch("/images.json")
          .then((res) => res.json())
          .then((data) => {
            setImages(data.images || []);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  };

  const handleFolderSelect = (folder: string) => {
    setFolderConfigured(true);
    setLoading(true);
    setTimeout(loadImages, 2000);
  };

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

  if (folderConfigured === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!folderConfigured) {
    return <FolderOnboarding onFolderSelect={handleFolderSelect} />;
  }

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
              <div className="grid grid-cols-2 gap-0 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                {Array.from({ length: 18 }).map((_, i) => (
                  <Skeleton
                    key={i}
                    className="mb-0 aspect-[3/4]"
                  />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-0 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
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
        images={filteredImages.map(img => ({
          ...img,
          src: img.src.startsWith("http") ? img.src : `${API_BASE}${img.src}`
        }))}
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
