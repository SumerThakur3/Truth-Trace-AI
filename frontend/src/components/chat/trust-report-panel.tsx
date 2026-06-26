"use client";

import { FileText, Shield, AlertTriangle, CheckCircle } from "lucide-react";
import type { TrustReport } from "@/types";
import { ConfidenceBadge } from "./confidence-badge";
import { VerificationTimeline } from "./verification-timeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

interface TrustReportPanelProps {
  report: TrustReport;
}

export function TrustReportPanel({ report }: TrustReportPanelProps) {
  const metrics = [
    { label: "Evidence Quality", value: report.evidence_quality },
    { label: "Source Reliability", value: report.source_reliability },
  ];

  const statusIcon = {
    verified: CheckCircle,
    partial: AlertTriangle,
    unverified: AlertTriangle,
  };

  const StatusIcon = statusIcon[report.verification_status];

  return (
    <Card className="glass-card">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-primary" />
          Trust Report
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <ConfidenceBadge score={report.confidence_score} size="lg" />

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-muted/50 p-3 text-center">
            <div className="text-2xl font-bold">{report.sources_checked}</div>
            <div className="text-xs text-muted-foreground">Sources Checked</div>
          </div>
          <div className="rounded-xl bg-muted/50 p-3 text-center">
            <div className="text-2xl font-bold text-trust-medium">{report.contradictions_found}</div>
            <div className="text-xs text-muted-foreground">Contradictions</div>
          </div>
        </div>

        {metrics.map((m) => (
          <div key={m.label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-muted-foreground">{m.label}</span>
              <span className="font-medium">{m.value}%</span>
            </div>
            <Progress value={m.value} className="h-1.5" />
          </div>
        ))}

        <div className="flex items-center gap-2 rounded-xl border p-3">
          <StatusIcon className="h-5 w-5 text-primary" />
          <div>
            <div className="text-sm font-medium capitalize">{report.verification_status}</div>
            <div className="text-xs text-muted-foreground">{report.final_trust_rating}</div>
          </div>
        </div>

        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1">
            <Shield className="h-3.5 w-3.5" /> Reasoning
          </h4>
          <p className="text-sm text-muted-foreground leading-relaxed">{report.reasoning}</p>
        </div>

        {report.timeline.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">
              Verification Timeline
            </h4>
            <VerificationTimeline steps={report.timeline} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
