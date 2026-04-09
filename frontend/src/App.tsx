import { FormEvent, KeyboardEvent, startTransition, useEffect, useMemo, useRef, useState } from "react";
import { EChartCard } from "./components/EChartCard";
import {
  buildReport,
  buildReportPdf,
  createSession,
  deleteSession,
  getComparison,
  getFinancial,
  getOverview,
  getSession,
  getSystemStatus,
  listSessions,
  renameSession,
  sendChatStream,
  type ChartData,
  type ChatMessage,
  type ComparisonResponse,
  type FinancialResponse,
  type NavKey,
  type OverviewResponse,
  type SessionSummary,
  type SystemStatusResponse,
} from "./lib/api";

const navItems: Array<{ key: NavKey; label: string; description: string }> = [
  { key: "chat", label: "对话", description: "问答、资料整合与图表分析" },
  { key: "financial", label: "财务", description: "查看当前标的的财务表格" },
  { key: "comparison", label: "对比", description: "查看同行对比与可视化" },
  { key: "report", label: "报告", description: "将当前会话导出为 HTML 报告" },
];

const acceptedFileTypes =
  ".png,.jpg,.jpeg,.webp,.gif,.bmp,.pdf,.xlsx,.xls,.csv,.doc,.docx,.txt,.md";

type ReportScope = "full" | "latest" | "recent3" | "custom";

interface ConversationRound {
  id: string;
  index: number;
  messages: ChatMessage[];
  userPrompt: string;
  assistantSummary: string;
}

function extractSymbol(target?: string | null) {
  const match = target?.match(/\d{6}/);
  return match?.[0] ?? "";
}

function dedupeStrings(values: Array<string | null | undefined>) {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const value of values) {
    const normalized = String(value ?? "").trim();
    if (!normalized || seen.has(normalized)) {
      continue;
    }
    seen.add(normalized);
    result.push(normalized);
  }

  return result;
}

const sourceContextPattern = /(来源|数据来源|资料来源|参考|引自|choice|wind|同花顺|东方财富|雪球|巨潮|ifind)/i;
const companySplitPattern = /(?:相较于|相比|对比|强于|弱于|优于|劣于|高于|低于|以及|与|和|及|、|的)/;
const companyStopwords = [
  "盈利能力",
  "分析主体",
  "当前分析",
  "核心赛道",
  "核心研判",
  "结论",
  "趋势",
  "来源",
  "财报",
  "年报",
  "季报",
  "数据",
  "报告",
  "行业",
  "赛道",
  "显著",
  "主体",
  "研判",
  "对比",
];

function normalizeCompanyCandidate(raw: string) {
  let candidate = raw
    .replace(/^(当前分析主体为|当前研究主体为|研究主体为|分析主体为|主体为|当前主体为|公司为|企业为|其中|关于)/, "")
    .trim()
    .replace(/^[：:，,。;；\s]+|[：:，,。;；\s]+$/g, "");

  const parts = candidate
    .split(companySplitPattern)
    .map((item) => item.trim().replace(/^[：:，,。;；\s]+|[：:，,。;；\s]+$/g, ""))
    .filter(Boolean);

  if (parts.length) {
    candidate = parts[parts.length - 1];
  }

  if (!candidate || candidate.length < 2 || candidate.length > 18) {
    return "";
  }
  if (!/[\u4e00-\u9fa5A-Za-z]/.test(candidate)) {
    return "";
  }
  if (companyStopwords.some((keyword) => candidate.includes(keyword))) {
    return "";
  }
  return candidate;
}

function extractStructuredTargetsFromText(text: string) {
  const normalized = String(text ?? "").replace(/\s+/g, " ").trim();
  if (!normalized) {
    return [] as Array<{ symbol: string; label: string }>;
  }

  const results: Array<{ symbol: string; label: string }> = [];
  const seen = new Set<string>();
  const pattern = /([A-Za-z0-9\u4e00-\u9fa5·]{2,30})\s*[（(]\s*(\d{6})(?:\.[A-Za-z]{2})?\s*[)）]/g;

  for (const match of normalized.matchAll(pattern)) {
    const rawLabel = match[1] ?? "";
    const symbol = match[2] ?? "";
    const startIndex = match.index ?? 0;
    const prefix = normalized.slice(Math.max(0, startIndex - 12), startIndex);
    if (sourceContextPattern.test(prefix)) {
      continue;
    }

    const company = normalizeCompanyCandidate(rawLabel);
    if (!company || !symbol) {
      continue;
    }

    const label = `${company}(${symbol})`;
    if (seen.has(label)) {
      continue;
    }
    seen.add(label);
    results.push({ symbol, label });
  }

  return results;
}

function deriveTargetsFromMessages(messages: ChatMessage[]) {
  const recentTargets: string[] = [];

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    const candidateTexts = [
      message.content,
      typeof message.payload?.body === "string" ? message.payload.body : "",
    ];

    for (const text of candidateTexts) {
      const matches = extractStructuredTargetsFromText(text);
      recentTargets.push(...matches.map((item) => item.symbol));
    }
  }

  return dedupeStrings(recentTargets);
}

function resolveTargetLabel(target: string, messages: ChatMessage[]) {
  const symbol = extractSymbol(target);
  if (!symbol) {
    return target;
  }

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    const candidateTexts = [
      typeof message.payload?.body === "string" ? message.payload.body : "",
      message.content,
    ];

    for (const text of candidateTexts) {
      const matched = extractStructuredTargetsFromText(text).find((item) => item.symbol === symbol);
      if (matched) {
        return matched.label;
      }
    }
  }

  return symbol;
}

function formatFileSize(file: File) {
  const sizeInKb = file.size / 1024;
  if (sizeInKb < 1024) {
    return `${sizeInKb.toFixed(1)} KB`;
  }
  return `${(sizeInKb / 1024).toFixed(1)} MB`;
}

function getFileKindLabel(file: File) {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "webp", "gif", "bmp"].includes(ext)) return "图片";
  if (ext === "pdf") return "PDF";
  if (["xlsx", "xls", "csv"].includes(ext)) return "表格";
  if (["doc", "docx"].includes(ext)) return "Word";
  if (["txt", "md"].includes(ext)) return "文本";
  return ext ? ext.toUpperCase() : "文件";
}

function extractFinancialPeriods(financial?: FinancialResponse | null) {
  if (!financial?.sections?.length) {
    return [];
  }

  const periods = new Set<string>();

  for (const section of financial.sections) {
    for (const row of section.rows ?? []) {
      const reportDate = row["\u62a5\u544a\u65e5"];
      const reportPeriod = row["\u62a5\u544a\u671f"];
      const candidate =
        typeof reportDate === "string" && reportDate.trim()
          ? reportDate.trim()
          : typeof reportPeriod === "string" && reportPeriod.trim()
            ? reportPeriod.trim()
            : "";

      if (candidate) {
        periods.add(candidate);
      }
    }
  }

  return Array.from(periods).sort((left, right) => right.localeCompare(left, "zh-CN"));
}

function normalizeRecordRows(value: unknown) {
  if (!Array.isArray(value)) {
    return [] as Array<Record<string, unknown>>;
  }
  return value.filter(
    (item): item is Record<string, unknown> =>
      Boolean(item) && typeof item === "object" && !Array.isArray(item),
  );
}

function normalizeStringList(value: unknown) {
  if (!Array.isArray(value)) {
    return [] as string[];
  }
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function summarizeText(text: string, maxLength = 88) {
  const normalized = text.replace(/\s+/g, " ").trim();
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength)}…`;
}

function buildConversationRounds(messages: ChatMessage[]) {
  const rounds: ConversationRound[] = [];
  let pendingMessages: ChatMessage[] = [];
  let currentUserPrompt = "";

  for (const message of messages) {
    if (message.role === "system") {
      continue;
    }

    if (message.role === "user") {
      if (pendingMessages.length) {
        const assistantMessages = pendingMessages
          .filter((item) => item.role === "assistant")
          .map((item) => item.content)
          .filter(Boolean);

        rounds.push({
          id: `round-${rounds.length + 1}`,
          index: rounds.length + 1,
          messages: pendingMessages,
          userPrompt: currentUserPrompt || "本轮未识别到明确提问",
          assistantSummary: summarizeText(
            assistantMessages[assistantMessages.length - 1] || "本轮尚未形成系统回答。",
            108,
          ),
        });
      }

      pendingMessages = [message];
      currentUserPrompt = summarizeText(message.content || "本轮未识别到明确提问");
      continue;
    }

    if (!pendingMessages.length) {
      pendingMessages = [message];
      currentUserPrompt = "系统延续回答";
    } else {
      pendingMessages.push(message);
    }
  }

  if (pendingMessages.length) {
    const assistantMessages = pendingMessages
      .filter((item) => item.role === "assistant")
      .map((item) => item.content)
      .filter(Boolean);

    rounds.push({
      id: `round-${rounds.length + 1}`,
      index: rounds.length + 1,
      messages: pendingMessages,
      userPrompt: currentUserPrompt || "本轮未识别到明确提问",
      assistantSummary: summarizeText(
        assistantMessages[assistantMessages.length - 1] || "本轮尚未形成系统回答。",
        108,
      ),
    });
  }

  return rounds;
}

function StatTile({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string | number;
  tone?: "default" | "accent";
}) {
  return (
    <div className={`stat-tile ${tone === "accent" ? "is-accent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function TargetSwitcher({
  options,
  value,
  onChange,
}: {
  options: Array<{ value: string; label: string }>;
  value?: string | null;
  onChange: (target: string) => void;
}) {
  if (options.length <= 1) {
    return null;
  }

  return (
    <div className="target-switcher">
      {options.map((option) => (
        <button
          key={option.value}
          className={`target-chip ${value === option.value ? "is-active" : ""}`}
          onClick={() => onChange(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function DataTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) {
    return <p className="table-empty">暂无可展示的数据。</p>;
  }

  const columns = Object.keys(rows[0] ?? {});

  return (
    <div className="table-shell__scroll">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`row-${rowIndex}`}>
              {columns.map((column) => (
                <td key={`${column}-${rowIndex}`}>{String(row[column] ?? "-")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function extractCharts(payload?: { chart?: ChartData | null; charts?: ChartData[] | null } | null): ChartData[] {
  if (!payload) {
    return [];
  }

  if (payload.charts?.length) {
    return payload.charts.filter((chart): chart is ChartData => Boolean(chart));
  }

  return payload.chart ? [payload.chart] : [];
}

function buildChartSignature(chart: ChartData) {
  return JSON.stringify({
    title: chart.title ?? chart.chart_name ?? "",
    chartType: chart.chart_type ?? "",
    xLabels: chart.x_labels ?? [],
    datasets: (chart.datasets ?? chart.series ?? []).map((dataset) => ({
      name: dataset.name,
      data: dataset.data,
    })),
  });
}

function dedupeCharts(charts: ChartData[]) {
  const seen = new Set<string>();
  const deduped: ChartData[] = [];

  for (const chart of charts) {
    const signature = buildChartSignature(chart);
    if (seen.has(signature)) {
      continue;
    }
    seen.add(signature);
    deduped.push(chart);
  }

  return deduped;
}

function cleanMessageContent(text: string) {
  if (!text) {
    return "";
  }

  return text
    .replace(/\[CHART_DATA\][\s\S]*?\[\/CHART_DATA\]/g, "")
    .replace(/\[CHART_DATA\][\s\S]*$/g, "")
    .trim();
}

function isMarkdownTableLine(line: string) {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|");
}

function isOrderedListLine(line: string) {
  return /^\d+\.\s+/.test(line.trim());
}

function isPlainSectionHeading(line: string) {
  const trimmed = line.trim();
  if (!trimmed || isMarkdownTableLine(trimmed) || isOrderedListLine(trimmed)) {
    return false;
  }
  if (/^[一二三四五六七八九十]+、.{1,24}$/.test(trimmed)) {
    return true;
  }
  if (/^[^。！？!?]{2,26}[：:]\s*$/.test(trimmed)) {
    return true;
  }
  return false;
}

function parseInlineLabelLine(line: string) {
  const trimmed = line.trim();
  const match = trimmed.match(
    /^(核心研判|核心结论|结论|分析主体|当前分析主体|核心数据整理|数据整理|整体判断|整体盈利差距|杜邦拆解动因|趋势层面|风险提示|补充说明|对比结论|核心依据|主要原因|驱动因素|数据来源|图表结论)[：:]\s*(.+)$/,
  );
  if (!match) {
    return null;
  }
  return { label: match[1], content: match[2] };
}

function renderTableBlock(tableLines: string[], keyPrefix: string) {
  const rows = tableLines.map((row) =>
    row
      .split("|")
      .slice(1, -1)
      .map((cell) => cell.trim()),
  );

  const dividerIndex = rows.findIndex((row) => row.every((cell) => /^:?-{3,}:?$/.test(cell)));
  const header = rows[0] ?? [];
  const body = rows.slice(dividerIndex >= 0 ? dividerIndex + 1 : 1).filter((row) => row.length > 0);

  return (
    <div className="message-table-container" key={`${keyPrefix}-table`}>
      <table className="markdown-table">
        <thead>
          <tr>
            {header.map((cell, index) => (
              <th key={`${keyPrefix}-head-${index}`}>{cell}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, rowIndex) => (
            <tr key={`${keyPrefix}-row-${rowIndex}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${keyPrefix}-cell-${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderTextBlock(textLines: string[], keyPrefix: string) {
  const elements: JSX.Element[] = [];
  let paragraphBuffer: string[] = [];
  let orderedListBuffer: string[] = [];

  function flushParagraph() {
    const content = paragraphBuffer.join("\n").trim();
    if (!content) {
      paragraphBuffer = [];
      return;
    }
    const isLead = !elements.length;
    elements.push(
      <p
        key={`${keyPrefix}-paragraph-${elements.length}`}
        className={`formatted-message__prose ${isLead ? "formatted-message__prose--lead" : ""}`}
      >
        {content}
      </p>,
    );
    paragraphBuffer = [];
  }

  function flushOrderedList() {
    if (!orderedListBuffer.length) {
      return;
    }
    elements.push(
      <ol key={`${keyPrefix}-list-${elements.length}`} className="formatted-message__ordered">
        {orderedListBuffer.map((item, index) => (
          <li key={`${keyPrefix}-list-item-${index}`}>{item}</li>
        ))}
      </ol>,
    );
    orderedListBuffer = [];
  }

  for (const rawLine of textLines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushOrderedList();
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushOrderedList();
      const level = headingMatch[1].length;
      const content = headingMatch[2].trim();
      if (level === 1) {
        elements.push(
          <h1 key={`${keyPrefix}-h1-${elements.length}`} className="formatted-message__h1">
            {content}
          </h1>,
        );
      } else if (level === 2) {
        elements.push(
          <h2 key={`${keyPrefix}-h2-${elements.length}`} className="formatted-message__h2">
            {content}
          </h2>,
        );
      } else {
        elements.push(
          <h3 key={`${keyPrefix}-h3-${elements.length}`} className="formatted-message__h3">
            {content}
          </h3>,
        );
      }
      continue;
    }

    const inlineLabel = parseInlineLabelLine(line);
    if (inlineLabel) {
      flushParagraph();
      flushOrderedList();
      elements.push(
        <div key={`${keyPrefix}-label-${elements.length}`} className="formatted-message__label-line">
          <span className="formatted-message__label">{inlineLabel.label}</span>
          <p className="formatted-message__label-content">{inlineLabel.content}</p>
        </div>,
      );
      continue;
    }

    if (isPlainSectionHeading(line)) {
      flushParagraph();
      flushOrderedList();
      elements.push(
        <h2 key={`${keyPrefix}-plain-heading-${elements.length}`} className="formatted-message__h2">
          {line.replace(/[：:]$/, "")}
        </h2>,
      );
      continue;
    }

    if (isOrderedListLine(line)) {
      flushParagraph();
      orderedListBuffer.push(line.replace(/^\d+\.\s+/, ""));
      continue;
    }

    paragraphBuffer.push(line);
  }

  flushParagraph();
  flushOrderedList();

  return (
    <div className="formatted-message__section" key={`${keyPrefix}-text`}>
      {elements}
    </div>
  );
}

function renderFormattedContent(text: string) {
  const cleaned = cleanMessageContent(text);
  if (!cleaned) {
    return null;
  }

  const lines = cleaned.split("\n");
  const blocks: Array<{ type: "text" | "table"; lines: string[] }> = [];
  let currentTextLines: string[] = [];
  let currentTableLines: string[] = [];

  for (const line of lines) {
    if (isMarkdownTableLine(line)) {
      if (currentTextLines.length) {
        blocks.push({ type: "text", lines: currentTextLines });
        currentTextLines = [];
      }
      currentTableLines.push(line.trim());
    } else {
      if (currentTableLines.length) {
        blocks.push({ type: "table", lines: currentTableLines });
        currentTableLines = [];
      }
      currentTextLines.push(line);
    }
  }

  if (currentTextLines.length) {
    blocks.push({ type: "text", lines: currentTextLines });
  }
  if (currentTableLines.length) {
    blocks.push({ type: "table", lines: currentTableLines });
  }

  return (
    <div className="formatted-message">
      {blocks.map((block, index) =>
        block.type === "table"
          ? renderTableBlock(block.lines, `block-${index}`)
          : renderTextBlock(block.lines, `block-${index}`),
      )}
    </div>
  );
}

export default function App() {
  const [nav, setNav] = useState<NavKey>("chat");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionTitleDraft, setSessionTitleDraft] = useState("");
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [streamingReply, setStreamingReply] = useState("");
  const [streamingCharts, setStreamingCharts] = useState<ChartData[]>([]);
  const [activeTarget, setActiveTarget] = useState<string | null>(null);
  const [activeTargets, setActiveTargets] = useState<string[]>([]);
  const [financialTarget, setFinancialTarget] = useState<string | null>(null);
  const [comparisonTarget, setComparisonTarget] = useState<string | null>(null);
  const [financial, setFinancial] = useState<FinancialResponse | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [reportHtml, setReportHtml] = useState("");
  const [reportScope, setReportScope] = useState<ReportScope>("full");
  const [selectedReportRoundIds, setSelectedReportRoundIds] = useState<string[]>([]);
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("准备开始新一轮研究。");
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const reportFrameRef = useRef<HTMLIFrameElement | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.session_id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  const conversationTargets = useMemo(() => {
    return dedupeStrings([activeTarget, ...activeTargets, ...deriveTargetsFromMessages(messages)]).filter((target) => {
      if (target === activeTarget) {
        return true;
      }
      const symbol = extractSymbol(target);
      if (!symbol) {
        return false;
      }
      return resolveTargetLabel(target, messages) !== symbol;
    });
  }, [activeTarget, activeTargets, messages]);
  const primaryConversationTarget = useMemo(() => {
    if (activeTarget && conversationTargets.includes(activeTarget)) {
      return activeTarget;
    }
    return conversationTargets[0] ?? null;
  }, [activeTarget, conversationTargets]);
  const targetOptions = useMemo(
    () =>
      conversationTargets.map((target) => ({
        value: target,
        label: resolveTargetLabel(target, messages),
      })),
    [conversationTargets, messages],
  );
  const selectedFinancialTarget = financialTarget ?? primaryConversationTarget;
  const selectedComparisonTarget = comparisonTarget ?? primaryConversationTarget;
  const selectedFinancialLabel = selectedFinancialTarget
    ? resolveTargetLabel(selectedFinancialTarget, messages)
    : "";
  const selectedComparisonLabel = selectedComparisonTarget
    ? resolveTargetLabel(selectedComparisonTarget, messages)
    : "";
  const financialPeriods = useMemo(() => extractFinancialPeriods(financial), [financial]);
  const latestFinancialPeriod = financialPeriods[0] ?? "";
  const comparisonSymbol = extractSymbol(selectedComparisonTarget);
  const latestAssistantMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "assistant") ?? null,
    [messages],
  );
  const latestAssistantCharts = useMemo(
    () => dedupeCharts(extractCharts(latestAssistantMessage?.payload ?? null)),
    [latestAssistantMessage],
  );
  const latestUserMessage = useMemo(
    () => [...messages].reverse().find((message) => message.role === "user") ?? null,
    [messages],
  );
  const comparisonSummary =
    typeof comparison?.scoring?.summary === "string" ? comparison.scoring.summary : "";
  const comparisonConclusion =
    typeof comparison?.scoring?.conclusion === "string" ? comparison.scoring.conclusion : "";
  const comparisonReasonLines = useMemo(
    () => normalizeStringList(comparison?.scoring?.reason_lines),
    [comparison?.scoring?.reason_lines],
  );
  const comparisonRankingRows = useMemo(
    () => normalizeRecordRows(comparison?.scoring?.ranking_rows),
    [comparison?.scoring?.ranking_rows],
  );
  const comparisonWeightRows = useMemo(
    () => normalizeRecordRows(comparison?.scoring?.weight_rows),
    [comparison?.scoring?.weight_rows],
  );
  const comparisonScoringStatus =
    typeof comparison?.scoring?.status === "string" ? comparison.scoring.status : "";
  const isNewChatMode = nav === "chat" && !messages.length && !streamingReply;
  const conversationRounds = useMemo(() => buildConversationRounds(messages), [messages]);
  const selectedReportRounds = useMemo(() => {
    if (reportScope === "custom") {
      return conversationRounds.filter((round) => selectedReportRoundIds.includes(round.id));
    }
    if (reportScope === "latest") {
      return conversationRounds.slice(-1);
    }
    if (reportScope === "recent3") {
      return conversationRounds.slice(-3);
    }
    return conversationRounds;
  }, [conversationRounds, reportScope, selectedReportRoundIds]);
  const selectedReportMessages = useMemo(() => {
    if (reportScope === "full") {
      return messages;
    }
    return selectedReportRounds.flatMap((round) => round.messages);
  }, [messages, reportScope, selectedReportRounds]);
  const reportSelectionLabel = useMemo(() => {
    if (reportScope === "full") {
      return "整段会话";
    }
    if (reportScope === "latest") {
      return "最近一轮";
    }
    if (reportScope === "recent3") {
      return "最近三轮";
    }
    return selectedReportRounds.length ? `已选 ${selectedReportRounds.length} 轮` : "未选择轮次";
  }, [reportScope, selectedReportRounds.length]);

  async function refreshSessions() {
    const nextSessions = await listSessions();
    startTransition(() => {
      setSessions(nextSessions);
    });
  }

  async function refreshOverview(messageCount = messages.length) {
    const [nextOverview, nextSystemStatus] = await Promise.all([
      getOverview(),
      getSystemStatus(messageCount),
    ]);
    setOverview(nextOverview);
    setSystemStatus(nextSystemStatus);
  }

  useEffect(() => {
    void refreshSessions().catch((nextError: unknown) => {
      setError(nextError instanceof Error ? nextError.message : "加载历史会话失败。");
    });

    void refreshOverview(0).catch((nextError: unknown) => {
      setError(nextError instanceof Error ? nextError.message : "加载系统概览失败。");
    });
  }, []);

  useEffect(() => {
    if (editingSessionId) {
      return;
    }
    if (activeSession) {
      setSessionTitleDraft(activeSession.title);
    } else {
      setSessionTitleDraft("");
    }
  }, [activeSession, editingSessionId]);

  useEffect(() => {
    void getSystemStatus(messages.length)
      .then((nextStatus) => setSystemStatus(nextStatus))
      .catch(() => undefined);
  }, [messages.length]);

  useEffect(() => {
    const nextPrimaryTarget = primaryConversationTarget;
    setFinancialTarget((current) =>
      current && conversationTargets.includes(current) ? current : nextPrimaryTarget,
    );
    setComparisonTarget((current) =>
      current && conversationTargets.includes(current) ? current : nextPrimaryTarget,
    );
  }, [conversationTargets, primaryConversationTarget]);

  useEffect(() => {
    const latestRoundId = conversationRounds[conversationRounds.length - 1]?.id;
    setSelectedReportRoundIds(latestRoundId ? [latestRoundId] : []);
  }, [conversationRounds]);

  useEffect(() => {
    setReportHtml("");
  }, [messages, primaryConversationTarget, reportScope, selectedReportRoundIds]);

  useEffect(() => {
    if (nav !== "financial" || !selectedFinancialTarget) {
      return;
    }

    setLoading(true);
    setError(null);
    setFinancial(null);
    void getFinancial(selectedFinancialTarget)
      .then((response) => setFinancial(response))
      .catch((nextError: unknown) => {
        setError(nextError instanceof Error ? nextError.message : "加载财务数据失败。");
      })
      .finally(() => setLoading(false));
  }, [nav, selectedFinancialTarget]);

  useEffect(() => {
    if (nav !== "comparison" || !comparisonSymbol) {
      return;
    }

    setLoading(true);
    setError(null);
    setComparison(null);
    void getComparison(comparisonSymbol)
      .then((response) => setComparison(response))
      .catch((nextError: unknown) => {
        setError(nextError instanceof Error ? nextError.message : "加载对比数据失败。");
      })
      .finally(() => setLoading(false));
  }, [nav, comparisonSymbol]);

  function openFilePicker() {
    fileInputRef.current?.click();
  }

  function handleFilesSelected(fileList: FileList | null) {
    if (!fileList) {
      return;
    }

    const nextFiles = Array.from(fileList);
    setSelectedFiles((current) => {
      const merged = [...current];
      for (const file of nextFiles) {
        const exists = merged.some(
          (item) =>
            item.name === file.name &&
            item.size === file.size &&
            item.lastModified === file.lastModified,
        );
        if (!exists) {
          merged.push(file);
        }
      }
      return merged;
    });
  }

  function removeSelectedFile(targetFile: File) {
    setSelectedFiles((current) =>
      current.filter(
        (file) =>
          !(
            file.name === targetFile.name &&
            file.size === targetFile.size &&
            file.lastModified === targetFile.lastModified
          ),
      ),
    );
  }

  async function openSession(sessionId: string) {
    setLoading(true);
    setError(null);
    try {
      const detail = await getSession(sessionId);
      const restoredTargets = dedupeStrings([
        detail.active_target,
        ...(detail.active_targets ?? []),
        ...deriveTargetsFromMessages(detail.messages),
      ]);
      const restoredPrimaryTarget =
        detail.active_target && restoredTargets.includes(detail.active_target)
          ? detail.active_target
          : restoredTargets[0] ?? null;
      setActiveSessionId(detail.session.session_id);
      setMessages(detail.messages);
      setStreamingReply("");
      setStreamingCharts([]);
      setSelectedFiles([]);
      setActiveTarget(restoredPrimaryTarget);
      setActiveTargets(restoredTargets);
      setFinancialTarget(restoredPrimaryTarget);
      setComparisonTarget(restoredPrimaryTarget);
      setFinancial(null);
      setComparison(null);
      setReportHtml("");
      setStatusText(`已打开会话：${detail.session.title}`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "打开会话失败。");
    } finally {
      setLoading(false);
    }
  }

  async function handleNewSession() {
    setLoading(true);
    setError(null);
    try {
      const detail = await createSession();
      setActiveSessionId(detail.session.session_id);
      setMessages([]);
      setPrompt("");
      setSelectedFiles([]);
      setStreamingReply("");
      setStreamingCharts([]);
      setActiveTarget(null);
      setActiveTargets([]);
      setFinancialTarget(null);
      setComparisonTarget(null);
      setFinancial(null);
      setComparison(null);
      setReportHtml("");
      setStatusText("新会话已创建，可以开始提问或上传资料。");
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建新会话失败。");
    } finally {
      setLoading(false);
    }
  }

  async function handleRenameSession(sessionId?: string, title?: string) {
    const targetSessionId = sessionId ?? activeSessionId;
    const nextTitle = (title ?? sessionTitleDraft).trim();
    if (!targetSessionId || !nextTitle) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const detail = await renameSession(targetSessionId, nextTitle);
      if (targetSessionId === activeSessionId) {
        setSessionTitleDraft(detail.session.title);
      }
      setEditingSessionId(null);
      setStatusText(`会话已重命名为：${detail.session.title}`);
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "重命名会话失败。");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteSession(sessionId?: string) {
    const targetSessionId = sessionId ?? activeSessionId;
    if (!targetSessionId) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await deleteSession(targetSessionId);
      setEditingSessionId((current) => (current === targetSessionId ? null : current));
      if (targetSessionId === activeSessionId) {
        setActiveSessionId(null);
        setMessages([]);
        setPrompt("");
        setSelectedFiles([]);
        setStreamingReply("");
        setStreamingCharts([]);
        setActiveTarget(null);
        setActiveTargets([]);
        setFinancialTarget(null);
        setComparisonTarget(null);
        setFinancial(null);
        setComparison(null);
        setReportHtml("");
        setSessionTitleDraft("");
      }
      setStatusText("当前会话已删除。");
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "删除会话失败。");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendPrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmed = prompt.trim();
    const effectivePrompt =
      trimmed || (selectedFiles.length ? "请结合我上传的文件内容进行分析，并在需要时生成图表。" : "");

    if ((!effectivePrompt && !selectedFiles.length) || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setStreamingReply("");
    setStreamingCharts([]);
    setStatusText("AI 正在处理你的问题和附件内容...");

    const optimisticMessages = [...messages, { role: "user" as const, content: effectivePrompt }];
    setMessages(optimisticMessages);
    setPrompt("");

    try {
      await sendChatStream(
        {
          prompt: effectivePrompt,
          sessionId: activeSessionId,
          chatHistory: messages,
          activeTarget,
          activeTargets,
          files: selectedFiles,
        },
        {
          onChunk: (chunk) => {
            setStreamingReply((current) => current + chunk);
          },
          onDone: (done) => {
            const nextTargets = dedupeStrings([
              done.active_target,
              ...(done.active_targets ?? []),
              ...deriveTargetsFromMessages(done.messages),
            ]);
            const nextPrimaryTarget =
              done.active_target && nextTargets.includes(done.active_target)
                ? done.active_target
                : nextTargets[0] ?? null;
            setMessages(done.messages);
            setActiveSessionId(done.session_id);
            setActiveTarget(nextPrimaryTarget);
            setActiveTargets(nextTargets);
            setFinancialTarget(nextPrimaryTarget);
            setComparisonTarget(nextPrimaryTarget);
            setStreamingReply("");
            setStreamingCharts([]);
            setSelectedFiles([]);
            setStatusText("回答已生成，右侧图表区域会同步展示可视化内容。");
          },
          onError: (message) => {
            setError(message);
          },
        },
      );
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "发送消息失败。");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateReport() {
    if (!selectedReportMessages.length) {
      setError("请先进行对话，再生成报告。");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await buildReport(selectedReportMessages, primaryConversationTarget);
      setReportHtml(response.html);
      setStatusText(`研究报告已生成：${reportSelectionLabel}。`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "生成报告失败。");
    } finally {
      setLoading(false);
    }
  }

  function toggleReportRound(roundId: string) {
    setSelectedReportRoundIds((current) =>
      current.includes(roundId) ? current.filter((item) => item !== roundId) : [...current, roundId],
    );
  }

  function handleDownloadReport() {
    if (!reportHtml) {
      return;
    }

    const blob = new Blob([reportHtml], { type: "text/html;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `research_report_${Date.now()}.html`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function handleDownloadReportPdf() {
    if (!selectedReportMessages.length) {
      setError("请先生成或选择报告内容，再导出 PDF。");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const { blob, filename } = await buildReportPdf(selectedReportMessages, primaryConversationTarget);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setStatusText(`研究报告 PDF 已导出：${reportSelectionLabel}。`);
    } catch (nextError) {
      const printWindow = reportFrameRef.current?.contentWindow;
      if (printWindow && reportHtml) {
        printWindow.focus();
        printWindow.print();
        setStatusText(`已打开浏览器打印导出，可直接另存为 PDF：${reportSelectionLabel}。`);
      } else {
        setError(nextError instanceof Error ? nextError.message : "导出 PDF 失败。");
      }
    } finally {
      setLoading(false);
    }
  }

  function renderComposer(variant: "default" | "hero" = "default") {
    function handleTextareaKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
      if (event.key !== "Enter") {
        return;
      }

      if (event.nativeEvent.isComposing) {
        return;
      }

      if (event.ctrlKey) {
        return;
      }

      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }

    return (
      <div className={`composer-wrap ${variant === "hero" ? "composer-wrap--hero" : ""}`}>
        {selectedFiles.length ? (
          <div className="file-tray">
            {selectedFiles.map((file) => (
              <span
                key={`${file.name}-${file.size}-${file.lastModified}`}
                className="file-chip"
                title={`${file.name} · ${formatFileSize(file)}`}
              >
                <span className="file-chip__label">{file.name}</span>
                <span className="file-chip__meta">
                  {getFileKindLabel(file)} · {formatFileSize(file)}
                </span>
                <button
                  className="file-chip__remove"
                  type="button"
                  aria-label={`移除 ${file.name}`}
                  onClick={() => removeSelectedFile(file)}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        ) : null}

        <form
          className={`composer ${variant === "hero" ? "composer--hero" : ""}`}
          onSubmit={(formEvent) => void handleSendPrompt(formEvent)}
        >
          <input
            ref={fileInputRef}
            className="composer-file-input"
            type="file"
            multiple
            accept={acceptedFileTypes}
            onChange={(changeEvent) => {
              handleFilesSelected(changeEvent.target.files);
              changeEvent.currentTarget.value = "";
            }}
          />
          <button
            className="composer-icon composer-icon--attach"
            type="button"
            aria-label="上传文件"
            title="上传图片、PDF、Excel、Word、文本等文件"
            onClick={openFilePicker}
          >
            +
          </button>
          <textarea
            value={prompt}
            onChange={(changeEvent) => setPrompt(changeEvent.target.value)}
            onKeyDown={handleTextareaKeyDown}
            placeholder="输入问题，或点击左侧 + 上传图片、PDF、Excel、Word 等文件一起分析"
            rows={1}
          />
          <button
            className="composer-send-button"
            disabled={loading || (!prompt.trim() && !selectedFiles.length)}
            type="submit"
            title="发送"
          >
            {loading ? "…" : "↑"}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className={`app-shell ${isNewChatMode ? "app-shell--new-chat" : ""}`}>
      <aside className="sidebar">
        <div className="brand-card">
          <img src="/assets/logo.png" alt="Logo" className="brand-card__logo" />
          <div className="brand-card__info">
            <h1>光之耀面</h1>
            <span className="brand-card__desc">企业级投研助手</span>
          </div>
        </div>

        <button className="primary-button" onClick={() => void handleNewSession()} type="button">
          新建对话
        </button>

        <section className="sidebar-section">
          <div className="sidebar-section__header">
            <span className="eyebrow">Sessions</span>
            <strong>{sessions.length}</strong>
          </div>
          <div className="session-list">
            {sessions.map((session) => {
              const isActive = activeSessionId === session.session_id;
              const isEditing = editingSessionId === session.session_id;

              return (
                <div key={session.session_id} className={`session-item ${isActive ? "is-active" : ""}`}>
                  {isEditing ? (
                    <div className="session-editing">
                      <input
                        autoFocus
                        value={sessionTitleDraft}
                        onBlur={() => {
                          const nextTitle = sessionTitleDraft.trim();
                          if (nextTitle) {
                            void handleRenameSession(session.session_id, nextTitle);
                          } else {
                            setEditingSessionId(null);
                            setSessionTitleDraft(isActive ? session.title : activeSession?.title ?? session.title);
                          }
                        }}
                        onChange={(changeEvent) => setSessionTitleDraft(changeEvent.target.value)}
                        onKeyDown={(event) => {
                          if (event.key === "Enter") {
                            event.preventDefault();
                            void handleRenameSession(session.session_id, sessionTitleDraft);
                          }
                          if (event.key === "Escape") {
                            setEditingSessionId(null);
                            setSessionTitleDraft(isActive ? session.title : activeSession?.title ?? session.title);
                          }
                        }}
                        placeholder="输入新的会话名称"
                      />
                    </div>
                  ) : (
                    <>
                      <button
                        className={`session-pill ${isActive ? "is-active" : ""}`}
                        onClick={() => void openSession(session.session_id)}
                        title={session.title}
                        type="button"
                      >
                        <span className="session-pill__title" title={session.title}>
                          {session.title}
                        </span>
                        <small className="session-pill__time">{session.updated_at ?? "刚刚更新"}</small>
                      </button>
                      <div className="session-item__actions">
                        <button
                          aria-label="重命名会话"
                          onClick={(event) => {
                            event.stopPropagation();
                            setEditingSessionId(session.session_id);
                            setSessionTitleDraft(session.title);
                          }}
                          title="重命名"
                          type="button"
                        >
                          <span className="session-action-icon">重</span>
                        </button>
                        <button
                          aria-label="删除会话"
                          className="is-danger"
                          onClick={(event) => {
                            event.stopPropagation();
                            void handleDeleteSession(session.session_id);
                          }}
                          title="删除"
                          type="button"
                        >
                          <span className="session-action-icon">删</span>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      </aside>

      <main
        className={`main-panel ${nav === "chat" && !isNewChatMode ? "main-panel--chat" : ""} ${isNewChatMode ? "main-panel--new-chat" : ""}`}
      >
        {!isNewChatMode ? (
          <header className="topbar">
            <nav className="nav-pills">
              {navItems.map((item) => (
                <button
                  key={item.key}
                  className={`nav-pill ${nav === item.key ? "is-active" : ""}`}
                  onClick={() => setNav(item.key)}
                  title={item.description}
                  type="button"
                >
                  {item.label}
                </button>
              ))}
            </nav>
          </header>
        ) : null}

        {error ? <div className="error-banner">{error}</div> : null}

        {nav === "chat" ? (
          isNewChatMode ? (
            <section className="new-chat-stage">
              <div className="new-chat-hero">
                <h1>开始一段新的研究对话</h1>
                <p className="new-chat-hero__subtitle">
                  输入问题，或直接把图片、PDF、Excel、Word、文本资料拖进工作流。历史对话保留在左侧，新对话页保持简洁聚焦，便于直接开始分析。
                </p>
                {renderComposer("hero")}
              </div>
            </section>
          ) : (
            <>
              <div className="chat-workspace-shell">
                <section className="unified-workspace-panel">
                  <div className="unified-timeline">
                    {messages.map((message, index) => {
                      const messageCharts =
                        message.role === "assistant" ? dedupeCharts(extractCharts(message.payload ?? null)) : [];
                      const isChartScrollable = messageCharts.length >= 3;

                      return (
                        <div
                          key={`timeline-${message.role}-${index}`}
                          className={`timeline-row ${message.role === "user" ? "is-user" : "is-assistant"}`}
                        >
                          <div className="message-side">
                            <article className={`message-bubble ${message.role === "user" ? "is-user" : "is-assistant"}`}>
                              <div className="message-bubble__meta">
                                {message.role === "user" ? "用户提问" : "AI 助手"}
                              </div>
                              <div className="message-bubble__body">
                                {renderFormattedContent(message.payload?.body ?? message.content)}
                              </div>
                              {message.payload?.sources?.length ? (
                                <div className="source-row">
                                  {message.payload.sources.map((source) => (
                                    <span key={source} className="source-chip">
                                      {source}
                                    </span>
                                  ))}
                                </div>
                              ) : null}
                            </article>
                          </div>

                          <div className="chart-side">
                            {message.role === "assistant" ? (
                              <div className="timeline-chart-panel">
                                <div className="timeline-chart-panel__header">
                                  <span className="eyebrow">对应可视化</span>
                                  <span className="timeline-chart-panel__count">
                                    {messageCharts.length ? `${messageCharts.length} 张图` : "本轮未生成图"}
                                  </span>
                                </div>
                                {messageCharts.length ? (
                                  <div className={`timeline-chart-stack ${isChartScrollable ? "is-scrollable" : ""}`}>
                                    {messageCharts.map((chart, chartIndex) => (
                                      <EChartCard key={`message-${index}-chart-${chartIndex}`} chart={chart} />
                                    ))}
                                  </div>
                                ) : (
                                  <div className="timeline-chart-empty">
                                    这一轮回答没有生成可视化，通常是因为当前内容缺少结构化数据或无需画图。
                                  </div>
                                )}
                              </div>
                            ) : (
                              <div className="timeline-spacer" />
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {streamingReply ? (
                      <div className="timeline-row is-assistant is-streaming">
                        <div className="message-side">
                          <article className="message-bubble is-assistant is-streaming">
                            <div className="message-bubble__meta">AI 助手生成中</div>
                            <div className="message-bubble__body">{renderFormattedContent(streamingReply)}</div>
                          </article>
                        </div>
                        <div className="chart-side">
                          <div className="timeline-chart-panel">
                            <div className="timeline-chart-panel__header">
                              <span className="eyebrow">对应可视化</span>
                              <span className="timeline-chart-panel__count">
                                {streamingCharts.length ? `${streamingCharts.length} 张图` : "等待图表生成"}
                              </span>
                            </div>
                            {streamingCharts.length ? (
                              <div className={`timeline-chart-stack ${streamingCharts.length >= 3 ? "is-scrollable" : ""}`}>
                                {streamingCharts.map((chart, chartIndex) => (
                                  <EChartCard key={`stream-chart-${chartIndex}`} chart={chart} />
                                ))}
                              </div>
                            ) : (
                              <div className="timeline-chart-empty">
                                图表会在当前轮回答生成完成后自动出现在这里。
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ) : null}
                  </div>
                </section>

                <div className="chat-workspace-shell__composer">{renderComposer("default")}</div>
              </div>
            </>
          )
        ) : null}

        {nav === "financial" ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">{"\u8d22\u52a1"}</span>
                <h2>财务数据</h2>
              </div>
              <span className="panel-header__hint">{selectedFinancialLabel || "先在对话中识别一个标的"}</span>
            </div>

            {!primaryConversationTarget ? (
              <div className="empty-state compact">
                <h3>还没有识别到分析标的</h3>
                <p>当对话中出现公司名称或股票代码后，这里会自动抓取该公司的财务报表与财务指标。</p>
              </div>
            ) : (
              <>
                <TargetSwitcher
                  options={targetOptions}
                  value={selectedFinancialTarget}
                  onChange={(target) => setFinancialTarget(target)}
                />

                <div className="overview-strip overview-strip--financial">
                  <StatTile label="当前标的" value={selectedFinancialLabel || "-"} tone="accent" />
                  <StatTile label="数据源" value={financial?.source ?? "加载中"} />
                  <StatTile label="单位提示" value={financial?.unit_hint ?? "-"} />
                  <StatTile label="财务分区数" value={financial?.sections?.length ?? 0} />
                </div>

                <div className="financial-disclosure-note">
                  <strong>{"\u62ab\u9732\u53e3\u5f84\u8bf4\u660e"}</strong>
                  <p>
                    {
                      "\u0041\u80a1\u901a\u5e38\u6ca1\u6709\u5355\u72ec\u7684\u201c\u56db\u5b63\u62a5\u201d\uff0c\u5b9a\u671f\u62a5\u544a\u4e00\u822c\u53ea\u6709\u4e00\u5b63\u62a5\u3001\u534a\u5e74\u62a5\u3001\u4e09\u5b63\u62a5\u548c\u5e74\u62a5\uff0c\u7b2c\u56db\u5b63\u5ea6\u6570\u636e\u5305\u542b\u5728\u5e74\u62a5\u91cc\u3002"
                    }
                    {latestFinancialPeriod
                      ? ` ${"\u5f53\u524d\u9875\u9762\u5c55\u793a\u7684\u6700\u65b0\u5df2\u62ab\u9732\u62a5\u544a\u671f\u4e3a"} ${latestFinancialPeriod}\uff1b${"\u5982\u679c\u8fd8\u6ca1\u6709\u5e74\u62a5\uff0c\u6700\u65b0\u4e00\u671f\u901a\u5e38\u5c31\u4f1a\u505c\u7559\u5728\u4e09\u5b63\u62a5\u3002"}`
                      : ` ${"\u5f53\u524d\u9875\u9762\u5c55\u793a\u7684\u662f\u516c\u5f00\u6570\u636e\u6e90\u91cc\u6700\u65b0\u5df2\u62ab\u9732\u7684\u8d22\u62a5\uff0c\u800c\u4e0d\u662f\u81ea\u7136\u65e5\u610f\u4e49\u4e0a\u7684\u6700\u65b0\u65e5\u671f\u3002"}`}
                  </p>
                </div>

                {financial?.has_data ? (
                  <div className="comparison-grid">
                    {(financial.sections?.length ? financial.sections : [{ key: "default", title: "财务数据", rows: financial.rows }]).map((section) => (
                      <section key={section.key} className="subpanel subpanel--full">
                        <span className="eyebrow">财务分区</span>
                        <h3>{section.title}</h3>
                        <div className="table-shell">
                          <DataTable rows={section.rows} />
                        </div>
                      </section>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state compact">
                    <h3>当前标的暂未返回财务数据</h3>
                    <p>{financial?.error ?? "正在抓取该公司的财务报表与财务指标。"}</p>
                  </div>
                )}
              </>
            )}
          </section>
        ) : null}

        {nav === "comparison" ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">{"\u5bf9\u6bd4"}</span>
                <h2>对比分析</h2>
              </div>
              <span className="panel-header__hint">{selectedComparisonLabel || "等待识别对比对象"}</span>
            </div>

            {!primaryConversationTarget ? (
              <div className="empty-state compact">
                <h3>还没有可对比的公司</h3>
                <p>当对话中出现一个或多个上市公司后，这里会优先展示对话里的公司对比，并补充行业对标。</p>
              </div>
            ) : (
              <>
                <TargetSwitcher
                  options={targetOptions}
                  value={selectedComparisonTarget}
                  onChange={(target) => setComparisonTarget(target)}
                />

                {false ? (
                  <>
                    <div className="overview-strip overview-strip--comparison">
                      <StatTile label="对话标的数" value={conversationTargets.length} tone="accent" />
                      <StatTile label="最新对比图数" value={latestAssistantCharts.length} />
                      <StatTile label="当前主标的" value={selectedComparisonLabel || "-"} />
                      <StatTile label="最新提问" value={latestUserMessage ? "已同步" : "暂无"} />
                    </div>

                    <div className="comparison-grid">
                      <section className="subpanel subpanel--full">
                        <span className="eyebrow">Conversation Comparison</span>
                        <h3>当前对话中的公司比较</h3>
                        <p>
                          这里优先展示本轮会话里最新形成的多公司对比结论和图表，保证“对比”页先反映当前聊天内容，再补充同行横向对标。
                        </p>
                        <div className="target-badge-row">
                          {targetOptions.map((option) => (
                            <span key={option.value} className="target-badge">
                              {option.label}
                            </span>
                          ))}
                        </div>
                        <div className="comparison-summary">
                          {renderFormattedContent(latestAssistantMessage?.payload?.body ?? latestAssistantMessage?.content ?? "")}
                        </div>
                      </section>

                      {latestAssistantCharts.length ? (
                        latestAssistantCharts.map((chart, chartIndex) => (
                          <div
                            key={`${chart.title ?? chart.chart_name ?? "conversation-chart"}-${chartIndex}`}
                            className="subpanel subpanel--full subpanel--chart"
                          >
                            <EChartCard chart={chart} />
                          </div>
                        ))
                      ) : (
                        <div className="empty-state compact comparison-inline-empty">
                          <h3>本轮对比还没有生成图表</h3>
                          <p>如果当前回答以结论为主而没有结构化数据，对比页会先展示文字结论；后续出现可量化数据时会自动补上图表。</p>
                        </div>
                      )}
                    </div>
                  </>
                ) : null}

                {comparisonSymbol ? (
                  <>
                    <div className="panel-section-title">
                      <span>行业对标</span>
                      <small>围绕当前选中的标的补充同行快照和赛道指标</small>
                    </div>

                    <div className="overview-strip overview-strip--comparison">
                      <StatTile
                        label="赛道"
                        value={comparison?.track_template?.track_name ?? "加载中"}
                        tone="accent"
                      />
                      <StatTile label="样本数" value={comparison?.snapshots.length ?? 0} />
                      <StatTile
                        label="覆盖率"
                        value={`${Math.round((comparison?.data_quality?.overall_coverage ?? 0) * 100)}%`}
                      />
                      <StatTile label="当前标的" value={selectedComparisonLabel || comparisonSymbol} />
                    </div>

                    <div className="comparison-grid">
                      <section className="subpanel subpanel--full comparison-verdict">
                        <span className="eyebrow">{"\u5bf9\u6807\u7ed3\u8bba"}</span>
                        <h3>{comparisonSummary || "正在生成同赛道对比结论"}</h3>
                        <p className="comparison-verdict__conclusion">
                          {comparisonConclusion || "系统正在根据同赛道样本计算相对位置、优势项和短板项。"}
                        </p>
                        {comparisonReasonLines.length ? (
                          <div className="comparison-verdict__list">
                            {comparisonReasonLines.map((line, index) => (
                              <p key={`comparison-reason-${index}`}>{line}</p>
                            ))}
                          </div>
                        ) : null}
                      </section>

                      <section className="subpanel">
                        <span className="eyebrow">{"\u8d5b\u9053\u805a\u7126"}</span>
                        <h3>{comparison?.track_template?.focus ?? "正在同步赛道说明"}</h3>
                        <p>这部分用于补足当前对话未覆盖的同行横向对比，帮助判断所选公司在赛道中的相对位置。</p>
                      </section>

                      <section className="subpanel">
                        <span className="eyebrow">{"\u6307\u6807\u8986\u76d6"}</span>
                        <DataTable rows={comparison?.data_quality?.metric_rows ?? []} />
                      </section>

                      {(comparison?.chart_specs ?? []).map((chart) => (
                        <div key={chart.title ?? chart.chart_name} className="subpanel subpanel--full subpanel--chart">
                          <EChartCard chart={chart} />
                        </div>
                      ))}

                      <div className="subpanel subpanel--full">
                        <span className="eyebrow">{"\u540c\u884c\u5feb\u7167"}</span>
                        <DataTable rows={comparison?.snapshots ?? []} />
                      </div>

                      <div className="subpanel">
                        <span className="eyebrow">{"\u7efc\u5408\u6392\u540d"}</span>
                        {comparisonRankingRows.length ? (
                          <DataTable rows={comparisonRankingRows} />
                        ) : (
                          <p className="table-empty">
                            {comparisonScoringStatus === "limited"
                              ? "当前可比样本或有效指标不足，暂不形成稳定综合排名。"
                              : "正在计算综合排名。"}
                          </p>
                        )}
                      </div>

                      <div className="subpanel">
                        <span className="eyebrow">{"\u8bc4\u5206\u4f9d\u636e"}</span>
                        {comparisonWeightRows.length ? (
                          <DataTable rows={comparisonWeightRows} />
                        ) : (
                          <p className="table-empty">当前还没有稳定的指标权重结果。</p>
                        )}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="empty-state compact">
                    <h3>当前标的暂未解析出股票代码</h3>
                    <p>如果对话里只有公司简称而没有明确证券代码，系统会先保留对话对比内容；补充代码后即可自动拉起同行对标。</p>
                  </div>
                )}
              </>
            )}
          </section>
        ) : null}

        {nav === "report" ? (
          <section className="panel report-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">报告</span>
                <h2>研究报告</h2>
              </div>
              <div className="report-actions">
                <button className="secondary-button" disabled={!reportHtml} onClick={handleDownloadReport} type="button">
                  下载 HTML
                </button>
                <button
                  className="secondary-button"
                  disabled={loading || !selectedReportMessages.length}
                  onClick={() => void handleDownloadReportPdf()}
                  type="button"
                >
                  导出 PDF
                </button>
                <button
                  className="primary-button primary-button--inline"
                  disabled={loading || !selectedReportMessages.length}
                  onClick={() => void handleGenerateReport()}
                  type="button"
                >
                  {loading ? "生成中..." : "生成报告"}
                </button>
              </div>
            </div>

            <div className="overview-strip">
              <StatTile label="消息数" value={messages.length} tone="accent" />
              <StatTile label="主标的" value={primaryConversationTarget ? resolveTargetLabel(primaryConversationTarget, messages) : "未识别"} />
              <StatTile label="关联标的数" value={conversationTargets.length} />
              <StatTile label="报告状态" value={reportHtml ? "已同步到当前会话" : "待生成"} />
            </div>

            <div className="report-scope-panel">
              <div className="report-scope-panel__header">
                <div>
                  <span className="eyebrow">生成范围</span>
                  <h3>按会话轮次灵活生成报告</h3>
                </div>
                <p>支持整段会话、最近一轮、最近三轮，以及自定义勾选若干轮次来单独生成报告。</p>
              </div>

              <div className="report-scope-switcher">
                {[
                  { key: "full", label: "整段会话" },
                  { key: "latest", label: "最近一轮" },
                  { key: "recent3", label: "最近三轮" },
                  { key: "custom", label: "自定义轮次" },
                ].map((option) => (
                  <button
                    key={option.key}
                    className={`report-scope-chip ${reportScope === option.key ? "is-active" : ""}`}
                    onClick={() => setReportScope(option.key as ReportScope)}
                    type="button"
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <div className="overview-strip overview-strip--report">
                <StatTile label="当前范围" value={reportSelectionLabel} tone="accent" />
                <StatTile label="覆盖轮次" value={selectedReportRounds.length || (reportScope === "full" ? conversationRounds.length : 0)} />
                <StatTile label="纳入消息数" value={selectedReportMessages.length} />
                <StatTile label="可选轮次" value={conversationRounds.length} />
              </div>

              {conversationRounds.length ? (
                <div className="report-round-list">
                  {conversationRounds.map((round) => {
                    const isSelected =
                      reportScope === "custom"
                        ? selectedReportRoundIds.includes(round.id)
                        : selectedReportRounds.some((item) => item.id === round.id);

                    return (
                      <button
                        key={round.id}
                        className={`report-round-card ${isSelected ? "is-active" : ""} ${reportScope !== "custom" ? "is-readonly" : ""}`}
                        onClick={() => {
                          if (reportScope === "custom") {
                            toggleReportRound(round.id);
                          } else {
                            setReportScope("custom");
                            setSelectedReportRoundIds([round.id]);
                          }
                        }}
                        type="button"
                      >
                        <span className="report-round-card__index">第 {round.index} 轮</span>
                        <strong>{round.userPrompt}</strong>
                        <p>{round.assistantSummary}</p>
                        <span className="report-round-card__meta">{round.messages.length} 条消息</span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>

            {targetOptions.length ? (
              <div className="target-badge-row">
                {targetOptions.map((option) => (
                  <span key={option.value} className="target-badge">
                    {option.label}
                  </span>
                ))}
              </div>
            ) : null}

            {reportHtml ? (
              <div className="report-preview-shell">
                <div className="report-preview-shell__header">
                  <span className="eyebrow">正式预览</span>
                  <p>当前版本已按企业研究报告版式生成，可直接预览、下载 HTML，或导出 PDF。</p>
                </div>
                <iframe
                  className="report-frame"
                  ref={reportFrameRef}
                  srcDoc={reportHtml}
                  title="研究报告预览"
                />
              </div>
            ) : messages.length ? (
              <div className="empty-state compact">
                <h3>报告尚未生成</h3>
                <p>
                  报告会基于当前会话的完整聊天内容生成。只要继续提问，财务、对比里的最新上下文都会自动带进报告，不会沿用旧结果。
                </p>
              </div>
            ) : (
              <div className="empty-state compact">
                <h3>请先完成一轮对话</h3>
                <p>当会话里已经形成分析内容后，就可以在这里导出对应的 HTML 研究报告。</p>
              </div>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}




