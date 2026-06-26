export interface Source {
  id: string;
  title: string;
  url: string;
  snippet: string;
  reliability_score: number;
  domain: string;
  extracted_evidence?: string[];
}

export interface Contradiction {
  claim: string;
  source_a: string;
  source_b: string;
  evidence_a: string;
  evidence_b: string;
  severity: "high" | "medium" | "low";
}

export interface TrustReport {
  sources_checked: number;
  verification_status: "verified" | "partial" | "unverified";
  confidence_score: number;
  evidence_quality: number;
  source_reliability: number;
  contradictions_found: number;
  final_trust_rating: string;
  reasoning: string;
  timeline: VerificationStep[];
}

export interface VerificationStep {
  step: string;
  status: "pending" | "running" | "completed" | "error";
  message: string;
  timestamp?: string;
}

export interface VerificationResult {
  id: string;
  question: string;
  answer: string;
  confidence_score: number;
  reliability_level: string;
  verification_status: string;
  sources: Source[];
  contradictions: Contradiction[];
  trust_report: TrustReport;
  claims: string[];
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  verification?: VerificationResult;
  isLoading?: boolean;
  streamingStep?: string;
}

export interface DashboardStats {
  total_queries: number;
  verification_rate: number;
  average_confidence: number;
  sources_used: number;
  confidence_trend: { date: string; score: number }[];
  verification_history: { date: string; verified: number; partial: number; unverified: number }[];
  source_reliability: { domain: string; score: number; count: number }[];
}

export interface StreamEvent {
  type: "step" | "sources" | "answer" | "complete" | "error";
  data: Record<string, unknown>;
}
