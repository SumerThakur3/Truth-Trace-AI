"use client";

import { useState, useRef, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import { Send, Shield, PanelRightOpen, PanelRightClose } from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { MessageBubble } from "@/components/chat/message-bubble";
import { TrustReportPanel } from "@/components/chat/trust-report-panel";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { streamVerify, verifyQuestion, API_BASE } from "@/lib/api";
import type { ChatMessage, VerificationResult, VerificationStep } from "@/types";

const DEMO_QUESTION = "What are the health benefits of Mediterranean diet according to recent research?";

const DEMO_RESULT: VerificationResult = {
  id: "demo-1",
  question: DEMO_QUESTION,
  answer:
    "The Mediterranean diet is consistently associated with significant cardiovascular benefits. Meta-analyses of over 1.5 million adults show a 30% reduction in cardiovascular disease risk (NEJM, 2023). Key benefits include improved lipid profiles, reduced inflammation markers (CRP reduction of 20-30%), and 25% lower type 2 diabetes incidence. The PREDIMED trial demonstrated a 30% reduction in major cardiovascular events among high-risk participants following a Mediterranean diet supplemented with extra-virgin olive oil or nuts.",
  confidence_score: 94,
  reliability_level: "High Confidence",
  verification_status: "verified",
  sources: [
    {
      id: "s1",
      title: "Primary Prevention of Cardiovascular Disease with Mediterranean Diet",
      url: "https://www.nejm.org/doi/full/10.1056/NEJMoa1800389",
      snippet: "The PREDIMED trial demonstrated significant cardiovascular benefits...",
      reliability_score: 98,
      domain: "nejm.org",
      extracted_evidence: [
        "30% reduction in major cardiovascular events in PREDIMED trial",
        "Mediterranean diet with olive oil showed strongest protective effect",
      ],
    },
    {
      id: "s2",
      title: "Mediterranean Diet and Health Outcomes - WHO Review",
      url: "https://www.who.int/nutrition/topics/mediterranean-diet",
      snippet: "WHO recognizes Mediterranean dietary patterns as evidence-based...",
      reliability_score: 96,
      domain: "who.int",
      extracted_evidence: [
        "Associated with reduced all-cause mortality",
        "Recommended dietary pattern for chronic disease prevention",
      ],
    },
    {
      id: "s3",
      title: "Effects on Inflammatory Markers - Lancet Meta-analysis",
      url: "https://www.thelancet.com/mediterranean-inflammation",
      snippet: "Systematic review of 45 studies shows CRP reduction of 20-30%...",
      reliability_score: 92,
      domain: "thelancet.com",
      extracted_evidence: ["CRP reduction of 20-30% across multiple studies"],
    },
  ],
  contradictions: [],
  claims: [
    "30% reduction in cardiovascular disease risk",
    "CRP reduction of 20-30%",
    "25% lower type 2 diabetes incidence",
  ],
  trust_report: {
    sources_checked: 12,
    verification_status: "verified",
    confidence_score: 94,
    evidence_quality: 91,
    source_reliability: 95,
    contradictions_found: 0,
    final_trust_rating: "Highly Trustworthy",
    reasoning:
      "All three primary claims were corroborated by multiple high-reliability sources including peer-reviewed medical journals and WHO guidelines. No contradictions detected across 12 sources analyzed.",
    timeline: [
      { step: "Question Analysis", status: "completed", message: "Health/nutrition domain, moderate complexity" },
      { step: "Web Search", status: "completed", message: "12 sources retrieved from trusted medical databases" },
      { step: "Claim Extraction", status: "completed", message: "3 verifiable claims identified" },
      { step: "Fact Verification", status: "completed", message: "All claims verified across multiple sources" },
      { step: "Contradiction Check", status: "completed", message: "No contradictions found" },
      { step: "Trust Report", status: "completed", message: "High confidence rating generated" },
    ],
  },
  created_at: new Date().toISOString(),
};

function ChatContent() {
  const searchParams = useSearchParams();
  const isDemo = searchParams.get("demo") === "true";
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState(isDemo ? DEMO_QUESTION : "");
  const [isLoading, setIsLoading] = useState(false);
  const [showReport, setShowReport] = useState(true);
  const [activeReport, setActiveReport] = useState<VerificationResult | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (isDemo && messages.length === 0) {
      handleSubmit(undefined, DEMO_QUESTION, true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDemo]);

  const handleSubmit = async (
    e?: React.FormEvent,
    questionOverride?: string,
    isDemoRun?: boolean
  ) => {
    e?.preventDefault();
    const question = (questionOverride || input).trim();
    if (!question || isLoading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: question,
    };

    const assistantId = `assistant-${Date.now()}`;
    const loadingMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      isLoading: true,
      streamingStep: "Analyzing question...",
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setInput("");
    setIsLoading(true);
    setActiveReport(null);

    if (isDemoRun) {
      const steps = [
        "Analyzing question...",
        "Searching trusted sources...",
        "Extracting claims...",
        "Verifying facts...",
        "Checking contradictions...",
        "Generating trust report...",
      ];
      for (let i = 0; i < steps.length; i++) {
        await new Promise((r) => setTimeout(r, 600));
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streamingStep: steps[i] } : m
          )
        );
      }
      await new Promise((r) => setTimeout(r, 400));
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? {
                ...m,
                content: DEMO_RESULT.answer,
                isLoading: false,
                verification: DEMO_RESULT,
              }
            : m
        )
      );
      setActiveReport(DEMO_RESULT);
      setIsLoading(false);
      return;
    }

    try {
      let result: VerificationResult | null = null;

      for await (const event of streamVerify(question)) {
        if (event.type === "step") {
          const step = event.data as VerificationStep;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, streamingStep: (step as { message: string }).message }
                : m
            )
          );
        } else if (event.type === "answer") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: (event.data as { answer: string }).answer }
                : m
            )
          );
        } else if (event.type === "complete") {
          result = event.data as VerificationResult;
        }
      }

      if (result) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: result!.answer,
                  isLoading: false,
                  verification: result!,
                }
              : m
          )
        );
        setActiveReport(result);
      } else {
        // Stream ended without a result — try the non-stream endpoint
        throw new Error("No complete event received");
      }
    } catch (streamError) {
      const errMsg = streamError instanceof Error ? streamError.message : "Stream failed";
      try {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, streamingStep: "Analyzing and verifying..." } : m
          )
        );
        const result = (await verifyQuestion(question)) as unknown as VerificationResult;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: result.answer, isLoading: false, verification: result }
              : m
          )
        );
        setActiveReport(result);
      } catch (fallbackError) {
        const detail =
          fallbackError instanceof Error ? fallbackError.message : errMsg;
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content: `Verification failed: ${detail}\n\nEnsure the backend is running at ${API_BASE} and GEMINI_API_KEY is set in backend/.env`,
                  isLoading: false,
                }
              : m
          )
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col pt-16">
      <Navbar />

      <div className="flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex-col">
          <div className="border-b px-6 py-3 flex items-center justify-between glass">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-primary" />
              <span className="font-semibold">TruthTrace Verification</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setShowReport(!showReport)}
              className="lg:hidden"
            >
              {showReport ? <PanelRightClose /> : <PanelRightOpen />}
            </Button>
          </div>

          <ScrollArea className="flex-1 px-6 py-4">
            {messages.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center h-full min-h-[400px] text-center"
              >
                <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-primary to-cyan-500 flex items-center justify-center mb-6 shadow-lg shadow-primary/30">
                  <Shield className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Ask Anything</h2>
                <p className="text-muted-foreground max-w-md mb-8">
                  Every answer comes with proof — confidence scores, sources, and trust reports.
                </p>
                <div className="grid gap-2 sm:grid-cols-2 max-w-lg">
                  {[
                    "Is climate change accelerating faster than predicted?",
                    "What are the latest findings on mRNA vaccine efficacy?",
                    "How does intermittent fasting affect longevity?",
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => setInput(q)}
                      className="text-left text-sm rounded-xl border p-3 hover:bg-muted/50 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </motion.div>
            ) : (
              <div className="space-y-6 max-w-3xl mx-auto pb-4">
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
                <div ref={scrollRef} />
              </div>
            )}
          </ScrollArea>

          <form onSubmit={handleSubmit} className="border-t p-4 glass">
            <div className="max-w-3xl mx-auto flex gap-3">
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit();
                  }
                }}
                placeholder="Ask a question to verify..."
                rows={1}
                className="flex-1 resize-none rounded-xl border bg-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                disabled={isLoading}
              />
              <Button
                type="submit"
                variant="gradient"
                size="icon"
                className="h-12 w-12 shrink-0"
                disabled={isLoading || !input.trim()}
              >
                <Send className="h-5 w-5" />
              </Button>
            </div>
          </form>
        </div>

        {showReport && activeReport && (
          <motion.aside
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="hidden lg:block w-96 border-l p-4 overflow-y-auto bg-muted/20"
          >
            <TrustReportPanel report={activeReport.trust_report} />
          </motion.aside>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={<div className="h-screen flex items-center justify-center">Loading...</div>}>
      <ChatContent />
    </Suspense>
  );
}
