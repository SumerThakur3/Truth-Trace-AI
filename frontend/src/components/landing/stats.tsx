"use client";

import { useEffect, useState } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";
import { apiFetch } from "@/lib/api";
import type { DashboardStats } from "@/types";

function AnimatedCounter({ value, suffix = "" }: { value: number; suffix?: string }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (v) => Math.round(v).toLocaleString());
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    const controls = animate(count, value, { duration: 2.5, ease: "easeOut" });
    const unsub = rounded.on("change", (v) => setDisplay(v));
    return () => {
      controls.stop();
      unsub();
    };
  }, [value, count, rounded]);

  return (
    <span>
      {display}
      {suffix}
    </span>
  );
}

export function StatsSection() {
  const [dashboardStats, setDashboardStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    let active = true;

    const fetchStats = async () => {
      try {
        const data = await apiFetch<DashboardStats>("/api/v1/dashboard/stats");
        if (active) setDashboardStats(data);
      } catch {
        if (active) setDashboardStats(null);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  const stats = [
    { label: "Questions Verified", value: dashboardStats?.total_queries ?? 0, suffix: "" },
    { label: "Sources Analyzed", value: dashboardStats?.sources_used ?? 0, suffix: "" },
    { label: "Avg Confidence", value: dashboardStats?.average_confidence ?? 0, suffix: "%" },
    { label: "Trust Reports Generated", value: dashboardStats?.total_queries ?? 0, suffix: "" },
  ];

  return (
    <section className="py-24 px-6">
      <div className="mx-auto max-w-7xl">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="glass-card p-8 md:p-12"
        >
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat, i) => (
              <motion.div
                key={stat.label}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="text-center"
              >
                <div className="text-4xl md:text-5xl font-bold gradient-text mb-2">
                  <AnimatedCounter value={stat.value} suffix={stat.suffix} />
                </div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
