"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";

export function PromptArea() {
  const [prompt, setPrompt] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (prompt.trim()) {
      console.log("Prompt:", prompt);
      setPrompt("");
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 z-50 w-full max-w-3xl -translate-x-1/2 px-4">
      <form onSubmit={handleSubmit}>
        <Input
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Type your prompt..."
          className="h-14 rounded-2xl border-0 bg-black px-6 text-base text-white shadow-2xl ring-1 ring-white/10 placeholder:text-white/40 focus-visible:ring-2 focus-visible:ring-white/30"
        />
      </form>
    </div>
  );
}
