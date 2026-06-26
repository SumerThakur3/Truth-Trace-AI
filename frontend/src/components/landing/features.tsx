"use client";

import { motion } from "framer-motion";
import {
  ShieldCheck,
  BarChart3,
  FileSearch,
  AlertTriangle,
  Globe,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const features = [
  {
    icon: ShieldCheck,
    title: "Fact Verification",
    description:
      "Multi-source verification engine cross-references claims against trusted databases and live web sources.",
    gradient: "from-emerald-500 to-teal-500",
  },
  {
    icon: BarChart3,
    title: "Confidence Scoring",
    description:
      "Every answer includes a transparent confidence percentage with reliability levels and verification status.",
    gradient: "from-primary to-purple-500",
  },
  {
    icon: FileSearch,
    title: "Trust Reports",
    description:
      "Detailed trust reports with evidence quality, source reliability, and comprehensive reasoning.",
    gradient: "from-cyan-500 to-blue-500",
  },
  {
    icon: AlertTriangle,
    title: "Contradiction Detection",
    description:
      "Automatically detects disagreements between sources with side-by-side evidence comparison.",
    gradient: "from-amber-500 to-orange-500",
  },
  {
    icon: Globe,
    title: "Source Transparency",
    description:
      "Full citation transparency with expandable evidence panels and direct source links.",
    gradient: "from-rose-500 to-pink-500",
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 },
  },
};

const item = {
  hidden: { opacity: 0, y: 30 },
  show: { opacity: 1, y: 0 },
};

export function FeaturesSection() {
  return (
    <section id="features" className="py-24 px-6">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            Built for <span className="gradient-text">Trust</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Enterprise-grade verification capabilities designed for accuracy,
            transparency, and confidence in every answer.
          </p>
        </motion.div>

        <motion.div
          variants={container}
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature) => (
            <motion.div key={feature.title} variants={item}>
              <Card className="glass-card h-full group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
                <CardHeader>
                  <div
                    className={`inline-flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br ${feature.gradient} shadow-lg mb-4 group-hover:scale-110 transition-transform`}
                  >
                    <feature.icon className="h-6 w-6 text-white" />
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                  <CardDescription className="leading-relaxed">
                    {feature.description}
                  </CardDescription>
                </CardHeader>
                <CardContent />
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
