"use client";

import { motion } from "framer-motion";
import { Search, Brain, CheckCircle2, FileText } from "lucide-react";

const steps = [
  {
    icon: Search,
    step: "01",
    title: "Ask Your Question",
    description: "Submit any question — our AI analyzes intent, domain, and complexity.",
  },
  {
    icon: Brain,
    step: "02",
    title: "Multi-Source Search",
    description: "Agents search trusted sources via Tavily, Serper, and RAG retrieval.",
  },
  {
    icon: CheckCircle2,
    step: "03",
    title: "Verify & Compare",
    description: "Claims are verified independently with contradiction detection.",
  },
  {
    icon: FileText,
    step: "04",
    title: "Trust Report",
    description: "Receive your answer with confidence score, evidence, and citations.",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="py-24 px-6 bg-muted/30">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            How It <span className="gradient-text">Works</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            A multi-agent pipeline that verifies every claim before delivering your answer.
          </p>
        </motion.div>

        <div className="relative">
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-primary/30 to-transparent -translate-y-1/2" />

          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            {steps.map((step, index) => (
              <motion.div
                key={step.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.15 }}
                className="relative"
              >
                <div className="glass-card p-6 text-center h-full hover:shadow-xl transition-shadow">
                  <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-cyan-500 shadow-lg shadow-primary/25 mb-4">
                    <step.icon className="h-7 w-7 text-white" />
                  </div>
                  <h3 className="text-lg font-semibold mt-2 mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {step.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
