"use client";

import { cn, getConfidenceBg, getConfidenceColor, getConfidenceLabel } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import { Shield } from "lucide-react";

interface ConfidenceBadgeProps {
  score: number;
  showBar?: boolean;
  size?: "sm" | "md" | "lg";
}

export function ConfidenceBadge({ score, showBar = true, size = "md" }: ConfidenceBadgeProps) {
  return (
    <div className={cn("rounded-xl border p-3", getConfidenceBg(score))}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Shield className={cn("h-4 w-4", getConfidenceColor(score))} />
          <span className={cn("font-semibold", getConfidenceColor(score), size === "sm" && "text-xs", size === "lg" && "text-lg")}>
            {score}%
          </span>
        </div>
        <span className={cn("text-xs font-medium", getConfidenceColor(score))}>
          {getConfidenceLabel(score)}
        </span>
      </div>
      {showBar && <Progress value={score} className="h-1.5" />}
    </div>
  );
}
