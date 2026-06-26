"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip as ChartTooltip,
  Legend,
} from "chart.js";
import { Bar as ChartBar } from "react-chartjs-2";
import {
  MessageSquare,
  ShieldCheck,
  TrendingUp,
  Globe,
  Loader2,
} from "lucide-react";
import { Navbar } from "@/components/layout/navbar";
import { Footer } from "@/components/layout/footer";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch } from "@/lib/api";
import type { DashboardStats } from "@/types";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, ChartTooltip, Legend);

const COLORS = ["#8b5cf6", "#06b6d4", "#10b981", "#f59e0b", "#ef4444"];

const fallbackStats: DashboardStats = {
  total_queries: 0,
  verification_rate: 0,
  average_confidence: 0,
  sources_used: 0,
  confidence_trend: [],
  verification_history: [],
  source_reliability: [],
};

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchStats = () => {
    apiFetch<DashboardStats>("/api/v1/dashboard/stats")
      .then(setStats)
      .catch(() => setStats(fallbackStats))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  const data = stats || fallbackStats;

  const analyticsCards = [
    { icon: MessageSquare, label: "Total Queries", value: data.total_queries.toLocaleString(), color: "from-primary to-purple-500" },
    { icon: ShieldCheck, label: "Verification Rate", value: `${data.verification_rate}%`, color: "from-emerald-500 to-teal-500" },
    { icon: TrendingUp, label: "Avg Confidence", value: `${data.average_confidence}%`, color: "from-cyan-500 to-blue-500" },
    { icon: Globe, label: "Sources Used", value: data.sources_used.toLocaleString(), color: "from-amber-500 to-orange-500" },
  ];

  const chartJsData = {
    labels: data.source_reliability.map((d) => d.domain),
    datasets: [
      {
        label: "Reliability",
        data: data.source_reliability.map((d) => d.score),
        backgroundColor: "rgba(6, 182, 212, 0.8)",
      },
    ],
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="min-h-screen flex items-center justify-center pt-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="pt-24 pb-16 px-6">
        <div className="mx-auto max-w-7xl">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-10"
          >
            <h1 className="text-3xl font-bold mb-2">Analytics Dashboard</h1>
            <p className="text-muted-foreground">
              Real-time verification metrics and trust analytics
            </p>
          </motion.div>

          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
            {analyticsCards.map((card, i) => (
              <motion.div
                key={card.label}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
                <Card className="glass-card overflow-hidden">
                  <CardContent className="p-6">
                    <div className={`inline-flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${card.color} mb-4`}>
                      <card.icon className="h-5 w-5 text-white" />
                    </div>
                    <div className="text-2xl font-bold">{card.value}</div>
                    <div className="text-sm text-muted-foreground">{card.label}</div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>

          <div className="grid gap-6 lg:grid-cols-2 mb-8">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-lg">Confidence Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={data.confidence_trend}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" className="text-xs" />
                    <YAxis domain={[0, 100]} className="text-xs" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "12px",
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="score"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={{ fill: "hsl(var(--primary))" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-lg">Verification History</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={data.verification_history}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="date" className="text-xs" />
                    <YAxis className="text-xs" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        borderRadius: "12px",
                      }}
                    />
                    <Bar dataKey="verified" fill="#10b981" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="partial" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-lg">Source Reliability</CardTitle>
              </CardHeader>
              <CardContent>
                <ChartBar
                  data={chartJsData}
                  options={{
                    responsive: true,
                    scales: { y: { min: 0, max: 100 } },
                    plugins: { legend: { position: "top" as const } },
                  }}
                />
              </CardContent>
            </Card>

            <Card className="glass-card">
              <CardHeader>
                <CardTitle className="text-lg">Top Source Domains</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={data.source_reliability}
                      dataKey="count"
                      nameKey="domain"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ domain, score }) => `${domain} (${score}%)`}
                    >
                      {data.source_reliability.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
