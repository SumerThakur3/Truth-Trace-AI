"use client";

import { motion } from "framer-motion";
import { User, Bot, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import type { ChatMessage } from "@/types";
import { ConfidenceBadge } from "./confidence-badge";
import { SourcePanel } from "./source-panel";
import { ContradictionAlert } from "./contradiction-alert";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-gradient-to-br from-primary to-cyan-500 text-white"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={cn("flex-1 max-w-[85%]", isUser && "text-right")}>
        <div
          className={cn(
            "inline-block rounded-2xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-md"
              : "glass-card rounded-tl-md text-left w-full"
          )}
        >
          {message.isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-muted-foreground">
                {message.streamingStep || "Verifying facts..."}
              </span>
            </div>
          ) : isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-h2:text-base prose-h3:text-sm prose-p:leading-relaxed prose-li:leading-relaxed prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-pre:bg-muted prose-pre:rounded-xl prose-pre:overflow-x-auto prose-table:text-xs prose-th:text-left prose-td:py-1">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}

          {message.verification && !message.isLoading && (
            <div className="mt-4 space-y-3 border-t border-border/50 pt-4">
              <ConfidenceBadge score={message.verification.confidence_score} />
              <ContradictionAlert contradictions={message.verification.contradictions} />
              <SourcePanel sources={message.verification.sources} />
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
