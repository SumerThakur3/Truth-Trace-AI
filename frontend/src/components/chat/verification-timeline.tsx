"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { VerificationStep } from "@/types";
import { cn } from "@/lib/utils";

interface VerificationTimelineProps {
  steps: VerificationStep[];
}

const statusIcon = {
  pending: Circle,
  running: Loader2,
  completed: CheckCircle2,
  error: XCircle,
};

const statusColor = {
  pending: "text-muted-foreground",
  running: "text-primary animate-spin",
  completed: "text-trust-high",
  error: "text-trust-low",
};

export function VerificationTimeline({ steps }: VerificationTimelineProps) {
  return (
    <div className="space-y-3">
      {steps.map((step, i) => {
        const Icon = statusIcon[step.status];
        return (
          <motion.div
            key={step.step}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
            className="flex items-start gap-3"
          >
            <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", statusColor[step.status])} />
            <div>
              <div className="text-sm font-medium">{step.step}</div>
              <div className="text-xs text-muted-foreground">{step.message}</div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
