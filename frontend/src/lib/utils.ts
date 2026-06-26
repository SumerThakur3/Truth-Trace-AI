import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export type ConfidenceLevel = "high" | "medium" | "low";

export function getConfidenceLevel(score: number): ConfidenceLevel {
  if (score >= 90) return "high";
  if (score >= 70) return "medium";
  return "low";
}

export function getConfidenceLabel(score: number): string {
  const level = getConfidenceLevel(score);
  if (level === "high") return "High Confidence";
  if (level === "medium") return "Medium Confidence";
  return "Low Confidence";
}

export function getConfidenceColor(score: number): string {
  const level = getConfidenceLevel(score);
  if (level === "high") return "text-trust-high";
  if (level === "medium") return "text-trust-medium";
  return "text-trust-low";
}

export function getConfidenceBg(score: number): string {
  const level = getConfidenceLevel(score);
  if (level === "high") return "bg-trust-high/10 border-trust-high/30";
  if (level === "medium") return "bg-trust-medium/10 border-trust-medium/30";
  return "bg-trust-low/10 border-trust-low/30";
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + "...";
}
