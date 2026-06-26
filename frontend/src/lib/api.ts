import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      cache: "no-store",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });
  } catch {
    throw new Error(
      `Cannot connect to backend at ${API_BASE}. Make sure the server is running.`
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    const detail = error.detail || error.message || `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return response.json();
}

export async function verifyQuestion(
  question: string,
  sessionId?: string
): Promise<Record<string, unknown>> {
  return apiFetch("/api/v1/verify", {
    method: "POST",
    body: JSON.stringify({ question, session_id: sessionId || "web" }),
  });
}

export async function* streamVerify(
  question: string,
  sessionId?: string
): AsyncGenerator<Record<string, unknown>> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/v1/verify/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, session_id: sessionId || "web" }),
    });
  } catch {
    throw new Error(
      `Cannot connect to backend at ${API_BASE}. Make sure the server is running.`
    );
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Stream failed" }));
    throw new Error(error.detail || `Stream failed (${response.status})`);
  }

  if (!response.body) {
    throw new Error("Stream response has no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith("data:")) {
        const payload = trimmed.slice(5).trim();
        if (!payload) continue;
        try {
          const event = JSON.parse(payload);
          if (event.type === "error") {
            throw new Error(event.data?.message || "Verification error");
          }
          yield event;
        } catch (e) {
          if (e instanceof Error && e.message !== "Verification error" && !e.message.startsWith("Verification")) {
            /* skip malformed JSON lines */
          } else if (e instanceof Error) {
            throw e;
          }
        }
      }
    }
  }
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/health`, { cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}
