"use client";

import { AlertTriangle } from "lucide-react";
import type { Contradiction } from "@/types";
import { cn } from "@/lib/utils";

interface ContradictionAlertProps {
  contradictions: Contradiction[];
}

export function ContradictionAlert({ contradictions }: ContradictionAlertProps) {
  if (!contradictions.length) return null;

  return (
    <div className="mt-4 space-y-3">
      <div className="flex items-center gap-2 text-trust-medium">
        <AlertTriangle className="h-4 w-4" />
        <span className="text-sm font-semibold">
          {contradictions.length} Contradiction{contradictions.length > 1 ? "s" : ""} Detected
        </span>
      </div>
      {contradictions.map((c, i) => (
        <div
          key={i}
          className={cn(
            "rounded-xl border p-4 space-y-3",
            c.severity === "high" && "border-trust-low/30 bg-trust-low/5",
            c.severity === "medium" && "border-trust-medium/30 bg-trust-medium/5",
            c.severity === "low" && "border-muted bg-muted/30"
          )}
        >
          <p className="text-sm font-medium">{c.claim}</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg bg-background p-3 text-xs">
              <div className="font-semibold text-muted-foreground mb-1">{c.source_a}</div>
              <p>{c.evidence_a}</p>
            </div>
            <div className="rounded-lg bg-background p-3 text-xs">
              <div className="font-semibold text-muted-foreground mb-1">{c.source_b}</div>
              <p>{c.evidence_b}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
