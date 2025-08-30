"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { File } from "lucide-react";

export type Artifact = {
  name: string;
  path: string; // workspace-relative or absolute accepted by backend
  mime?: string;
  previewable: boolean;
  downloadUrl: string;
  previewUrl?: string;
  runId?: string;
  workspaceId?: string; // sandboxId
};

interface ArtifactChipsProps {
  artifacts: Artifact[];
  onOpen: (path: string) => void;
}

export function ArtifactChips({ artifacts, onOpen }: ArtifactChipsProps) {
  if (!artifacts || artifacts.length === 0) return null;
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {artifacts.map((a) => (
        <Button
          key={a.path}
          variant="outline"
          size="sm"
          className="h-7 px-2 gap-2 rounded-full border-muted-foreground/30"
          onClick={() => onOpen(a.path)}
          title={a.path}
        >
          <File className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium">{a.name}</span>
        </Button>
      ))}
    </div>
  );
}

