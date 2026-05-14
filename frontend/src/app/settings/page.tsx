"use client";

import { TopNavbar } from "@/components/top-navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Save, Palette, Layout, Image as ImageIcon } from "lucide-react";
import Link from "next/link";

export default function SettingsPage() {
  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    alert("Settings saved!");
  };

  return (
    <div className="flex min-h-screen flex-col">
      <TopNavbar
        searchQuery=""
        onSearchChange={() => {}}
        sidebarOpen={true}
        onToggleSidebar={() => {}}
      />

      <main className="flex-1 overflow-auto px-4 py-6 md:px-6">
        <div className="mx-auto max-w-2xl">
          <div className="mb-6">
            <Link href="/" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-4">
              <ArrowLeft className="h-4 w-4" />
              Back to gallery
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
            <p className="text-muted-foreground mt-1">Configure your CLIPO preferences</p>
          </div>

          <form onSubmit={handleSave} className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Photo Folder</CardTitle>
                <CardDescription>Configure the location of your photo library</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="folder">Folder Path</Label>
                  <Input id="folder" placeholder="/home/user/Pictures" defaultValue="~/Pictures" />
                </div>
                <p className="text-sm text-muted-foreground">
                  CLIPO will scan this folder and index your photos for AI-powered search.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Search Settings</CardTitle>
                <CardDescription>Configure AI search behavior</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="api">API Endpoint</Label>
                  <Input id="api" placeholder="http://localhost:3001" defaultValue="http://localhost:3001" />
                </div>
                <div className="flex items-center gap-4">
                  <div className="flex items-center space-x-2">
                    <input type="checkbox" id="semantic" defaultChecked className="rounded" />
                    <Label htmlFor="semantic">Enable semantic search</Label>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Customize</CardTitle>
                <CardDescription>Personalize your CLIPO experience</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Gallery Layout</Label>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="gap-2">
                      <Layout className="h-4 w-4" />
                      Grid
                    </Button>
                    <Button variant="default" size="sm" className="gap-2">
                      <ImageIcon className="h-4 w-4" />
                      Masonry
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Theme Accent Color</Label>
                  <div className="flex gap-2">
                    <button type="button" className="h-8 w-8 rounded-full bg-primary ring-2 ring-offset-2 ring-primary" />
                    <button type="button" className="h-8 w-8 rounded-full bg-blue-500" />
                    <button type="button" className="h-8 w-8 rounded-full bg-green-500" />
                    <button type="button" className="h-8 w-8 rounded-full bg-purple-500" />
                    <button type="button" className="h-8 w-8 rounded-full bg-pink-500" />
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Palette className="h-4 w-4 text-muted-foreground" />
                    <Label>Compact sidebar icons</Label>
                  </div>
                  <input type="checkbox" className="rounded" />
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end gap-4">
              <Button variant="outline" type="button" onClick={() => window.history.back()}>
                Cancel
              </Button>
              <Button type="submit" className="gap-2">
                <Save className="h-4 w-4" />
                Save Changes
              </Button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}