"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ExternalLink, ChevronDown, Globe } from "lucide-react";
import type { Source } from "@/types";
import { cn, truncate } from "@/lib/utils";

interface SourcePanelProps {
  sources: Source[];
}

export function SourcePanel({ sources }: SourcePanelProps) {
  const [expanded, setExpanded] = useState<string | null>(null);

  if (!sources.length) return null;

  return (
    <div className="mt-4 space-y-2">
      <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
        <Globe className="h-3.5 w-3.5" />
        Sources ({sources.length})
      </h4>
      {sources.map((source) => (
        <div
          key={source.id}
          className="rounded-xl border bg-muted/30 overflow-hidden"
        >
          <button
            onClick={() => setExpanded(expanded === source.id ? null : source.id)}
            className="w-full flex items-center justify-between p-3 text-left hover:bg-muted/50 transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{source.title}</div>
              <div className="text-xs text-muted-foreground flex items-center gap-2 mt-0.5">
                <span>{source.domain}</span>
                <span className="text-trust-high">{source.reliability_score}% reliable</span>
              </div>
            </div>
            <ChevronDown
              className={cn(
                "h-4 w-4 shrink-0 transition-transform",
                expanded === source.id && "rotate-180"
              )}
            />
          </button>
          <AnimatePresence>
            {expanded === source.id && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="px-3 pb-3 space-y-2">
                  <p className="text-sm text-muted-foreground">{truncate(source.snippet, 300)}</p>
                  {source.extracted_evidence?.map((ev, i) => (
                    <div key={i} className="text-xs bg-background rounded-lg p-2 border-l-2 border-primary">
                      {ev}
                    </div>
                  ))}
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  >
                    Open source <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </div>
  );
}
