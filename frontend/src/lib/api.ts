export type NavKey = "chat" | "financial" | "comparison" | "report";

export interface ChatPayload {
  version?: string;
  source?: string;
  raw_text?: string;
  summary?: string;
  body?: string;
  sections?: Array<Record<string, unknown>>;
  sources?: string[];
  chart?: ChartData | null;
  charts?: ChartData[];
}

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
  payload?: ChatPayload | null;
}

export interface SessionSummary {
  session_id: string;
  title: string;
  updated_at?: string | null;
  filename?: string | null;
}

export interface SessionDetail {
  session: SessionSummary;
  messages: ChatMessage[];
  active_target?: string | null;
  active_targets?: string[];
}

export interface OverviewResponse {
  company_count: number;
  industry_count: number;
  avg_gross_margin: number;
}

export interface SystemStatusResponse {
  api_status?: string;
  kb_ready?: boolean;
  msg_count?: number;
}

export interface ChartSeries {
  name: string;
  data: number[];
  type?: string;
}

export interface ChartData {
  title?: string;
  chart_name?: string;
  chart_type?: string;
  x_labels?: string[];
  datasets?: ChartSeries[];
  series?: ChartSeries[];
  analyst_verdict?: string;
  strategic_highlight?: string;
}

export interface FinancialResponse {
  target: string;
  symbol?: string | null;
  has_data: boolean;
  source?: string | null;
  unit_hint?: string | null;
  rows: Array<Record<string, unknown>>;
  sections?: Array<{
    key: string;
    title: string;
    rows: Array<Record<string, unknown>>;
  }>;
  error?: string | null;
}

export interface ComparisonResponse {
  symbol: string;
  snapshots: Array<Record<string, unknown>>;
  chart_specs: ChartData[];
  track_template?: {
    track_name: string;
    focus: string;
    metrics: Array<{
      key: string;
      display_name: string;
      is_positive: boolean;
    }>;
  } | null;
  data_quality: {
    sample_count?: number;
    overall_coverage?: number;
    metric_rows?: Array<Record<string, unknown>>;
    source_stats?: Array<Record<string, unknown>>;
    latest_period_stats?: Array<Record<string, unknown>>;
  };
  scoring: {
    status?: string;
    summary?: string;
    conclusion?: string;
    reason_lines?: string[];
    sample_count?: number;
    metric_count?: number;
    target_name?: string;
    target_rank?: number;
    target_score?: number;
    ranking_rows?: Array<Record<string, unknown>>;
    weight_rows?: Array<Record<string, unknown>>;
    [key: string]: unknown;
  };
}

export interface ChatDoneEvent {
  type: "done";
  session_id: string;
  payload: ChatPayload;
  reply: string;
  active_target?: string | null;
  active_targets?: string[];
  detected_targets?: string[];
  messages: ChatMessage[];
}

interface StreamHandlers {
  onChunk: (chunk: string) => void;
  onDone: (event: ChatDoneEvent) => void;
  onError: (message: string) => void;
}

const rawApiBase = import.meta.env.VITE_API_BASE;
// Default to same-origin APIs so bundled builds work behind a single public URL.
const API_BASE = rawApiBase === undefined ? "" : rawApiBase.replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function listSessions() {
  return request<SessionSummary[]>("/api/sessions");
}

export function getSession(sessionId: string) {
  return request<SessionDetail>(`/api/sessions/${sessionId}`);
}

export function createSession(seedTitle?: string) {
  return request<SessionDetail>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ seed_title: seedTitle ?? null }),
  });
}

export function renameSession(sessionId: string, title: string) {
  return request<SessionDetail>(`/api/sessions/${sessionId}`, {
    method: "PUT",
    body: JSON.stringify({ title }),
  });
}

export function deleteSession(sessionId: string) {
  return request<{ deleted: boolean; session_id: string }>(`/api/sessions/${sessionId}`, {
    method: "DELETE",
  });
}

export function getOverview() {
  return request<OverviewResponse>("/api/dashboard/overview");
}

export function getSystemStatus(msgCount = 0) {
  return request<SystemStatusResponse>(`/api/dashboard/system-status?msg_count=${msgCount}`);
}

export function getFinancial(target: string) {
  return request<FinancialResponse>(`/api/financial/${encodeURIComponent(target)}`);
}

export function getComparison(symbol: string) {
  return request<ComparisonResponse>(`/api/comparison/${encodeURIComponent(symbol)}?limit=16`);
}

export function buildReport(messages: ChatMessage[], activeTarget?: string | null) {
  return request<{ html: string }>("/api/report", {
    method: "POST",
    body: JSON.stringify({
      messages,
      active_target: activeTarget ?? null,
    }),
  });
}

export async function buildReportPdf(messages: ChatMessage[], activeTarget?: string | null) {
  const response = await fetch(`${API_BASE}/api/report/pdf`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      messages,
      active_target: activeTarget ?? null,
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed: ${response.status}`);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = disposition.match(/filename="([^"]+)"/);
  return {
    blob,
    filename: match?.[1] ?? `research_report_${Date.now()}.pdf`,
  };
}

export async function sendChatStream(
  payload: {
    prompt: string;
    sessionId?: string | null;
    chatHistory: ChatMessage[];
    activeTarget?: string | null;
    activeTargets?: string[];
    files?: File[];
  },
  handlers: StreamHandlers,
) {
  const formData = new FormData();
  formData.append("prompt", payload.prompt);
  if (payload.sessionId) {
    formData.append("session_id", payload.sessionId);
  }
  formData.append("chat_history", JSON.stringify(payload.chatHistory));
  if (payload.activeTarget) {
    formData.append("active_target", payload.activeTarget);
  }
  formData.append("active_targets", JSON.stringify(payload.activeTargets ?? []));
  formData.append("persist", "true");

  if (payload.files && payload.files.length > 0) {
    for (const file of payload.files) {
      formData.append("files", file);
    }
  }

  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok || !response.body) {
    throw new Error("Unable to open chat stream.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const eventBlock of events) {
      const dataLine = eventBlock
        .split("\n")
        .find((line) => line.startsWith("data: "));

      if (!dataLine) {
        continue;
      }

      const payloadText = dataLine.slice(6);
      const event = JSON.parse(payloadText) as
        | { type: "chunk"; content: string }
        | ChatDoneEvent
        | { type: "error"; message: string };

      if (event.type === "chunk") {
        handlers.onChunk(event.content);
      } else if (event.type === "done") {
        handlers.onDone(event);
      } else if (event.type === "error") {
        handlers.onError(event.message);
      }
    }
  }
}
