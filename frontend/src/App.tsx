import { FormEvent, startTransition, useEffect, useMemo, useState } from "react";
import { EChartCard } from "./components/EChartCard";
import {
  buildReport,
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
  { key: "chat", label: "智能研判", description: "流式对话、结构化结论和图表洞察" },
  { key: "financial", label: "财务透视", description: "核心财务表与基础面快照" },
  { key: "comparison", label: "赛道对标", description: "同行对比、质量覆盖与评分" },
  { key: "report", label: "研究报告", description: "将会话整理成 HTML 报告" },
];

function extractSymbol(target?: string | null) {
  const match = target?.match(/\d{6}/);
  return match?.[0] ?? "";
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

function DataTable({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) {
    return <p className="table-empty">暂无数据</p>;
  }

  const columns = Object.keys(rows[0]);

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

// Helper to strip [CHART_DATA] blocks from text
function cleanMessageContent(text: string): string {
  if (!text) return "";
  const cleaned = text.replace(/\[CHART_DATA\][\s\S]*?\[\/CHART_DATA\]/g, "").trim();
  // Also catch unclosed tags during streaming
  return cleaned.replace(/\[CHART_DATA\][\s\S]*$/g, "").trim();
}

// Simple Markdown table parser to fulfill "regimented" requirement without new deps
function renderFormattedContent(text: string) {
  const cleaned = cleanMessageContent(text);
  if (!cleaned.includes("|")) {
    return <p style={{ whiteSpace: "pre-wrap" }}>{cleaned}</p>;
  }

  const lines = cleaned.split("\n");
  const tableData: string[] = [];
  const otherParts: string[] = [];
  let inTable = false;

  for (const line of lines) {
    if (line.trim().startsWith("|") && line.trim().endsWith("|")) {
      inTable = true;
      tableData.push(line);
    } else {
      if (inTable && line.trim() === "") continue; // Skip empty lines inside table
      otherParts.push(line);
      if (inTable) inTable = false; 
    }
  }

  if (tableData.length < 2) {
    return <p style={{ whiteSpace: "pre-wrap" }}>{cleaned}</p>;
  }

  const rows = tableData.map(row => 
    row.split("|")
      .filter((_, i, arr) => i > 0 && i < arr.length - 1)
      .map(c => c.trim())
  );
  
  const headerIdx = tableData.findIndex(line => line.includes("---"));
  const header = rows[0];
  const body = rows.slice(headerIdx !== -1 ? headerIdx + 1 : 1).filter(r => r.length > 0);

  return (
    <div className="formatted-message">
      {otherParts.length > 0 && <p style={{ whiteSpace: "pre-wrap", marginBottom: "1rem" }}>{otherParts.join("\n")}</p>}
      <div className="message-table-container">
        <table className="markdown-table">
          <thead>
            <tr>{header.map((h, i) => <th key={i}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri}>{row.map((cell, ci) => <td key={ci}>{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function App() {
  const [nav, setNav] = useState<NavKey>("chat");
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionTitleDraft, setSessionTitleDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [prompt, setPrompt] = useState("");
  const [streamingReply, setStreamingReply] = useState("");
  const [streamingChart, setStreamingChart] = useState<ChartData | null>(null);
  const [activeTarget, setActiveTarget] = useState<string | null>(null);
  const [activeTargets, setActiveTargets] = useState<string[]>([]);
  const [financial, setFinancial] = useState<FinancialResponse | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [reportHtml, setReportHtml] = useState("");
  const [overview, setOverview] = useState<OverviewResponse | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState("React 工作台已接管新的 API，可以开始逐步替换旧界面。");
  const [error, setError] = useState<string | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.session_id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

  const comparisonSymbol = extractSymbol(activeTarget);
  const allAssistantCharts = useMemo(
    () =>
      messages
        .filter((message) => message.role === "assistant" && message.payload?.chart)
        .map((message) => message.payload!.chart!),
    [messages],
  );

  async function refreshSessions() {
    const nextSessions = await listSessions();
    startTransition(() => {
      setSessions(nextSessions);
    });
  }

  async function refreshOverview() {
    const [nextOverview, nextSystemStatus] = await Promise.all([
      getOverview(),
      getSystemStatus(messages.length),
    ]);
    setOverview(nextOverview);
    setSystemStatus(nextSystemStatus);
  }

  useEffect(() => {
    void refreshSessions().catch((nextError: unknown) => {
      setError(nextError instanceof Error ? nextError.message : "加载会话失败");
    });
    void refreshOverview().catch((nextError: unknown) => {
      setError(nextError instanceof Error ? nextError.message : "加载总览信息失败");
    });
  }, []);

  useEffect(() => {
    if (activeSession) {
      setSessionTitleDraft(activeSession.title);
    }
  }, [activeSession]);

  useEffect(() => {
    void getSystemStatus(messages.length)
      .then((nextStatus) => setSystemStatus(nextStatus))
      .catch(() => undefined);
  }, [messages.length]);

  useEffect(() => {
    if (nav !== "financial" || !activeTarget) {
      return;
    }

    setLoading(true);
    setError(null);
    void getFinancial(activeTarget)
      .then((response) => {
        setFinancial(response);
      })
      .catch((nextError: unknown) => {
        setError(nextError instanceof Error ? nextError.message : "财务数据加载失败");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [nav, activeTarget]);

  useEffect(() => {
    if (nav !== "comparison" || !comparisonSymbol) {
      return;
    }

    setLoading(true);
    setError(null);
    void getComparison(comparisonSymbol)
      .then((response) => {
        setComparison(response);
      })
      .catch((nextError: unknown) => {
        setError(nextError instanceof Error ? nextError.message : "赛道对标数据加载失败");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [nav, comparisonSymbol]);

  async function openSession(sessionId: string) {
    setLoading(true);
    setError(null);
    try {
      const detail = await getSession(sessionId);
      setActiveSessionId(detail.session.session_id);
      setMessages(detail.messages);
      setStreamingReply("");
      setStreamingChart(null);
      setActiveTarget(null);
      setActiveTargets([]);
      setFinancial(null);
      setComparison(null);
      setStatusText(`已切换到会话「${detail.session.title}」`);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "打开会话失败");
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
      setStreamingReply("");
      setStreamingChart(null);
      setFinancial(null);
      setComparison(null);
      setReportHtml("");
      setActiveTarget(null);
      setActiveTargets([]);
      setStatusText("已创建新会话，现在可以开始新的分析任务。");
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "创建会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleRenameSession() {
    if (!activeSessionId || !sessionTitleDraft.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const detail = await renameSession(activeSessionId, sessionTitleDraft.trim());
      setStatusText(`已更新会话标题为「${detail.session.title}」`);
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "重命名会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleDeleteSession() {
    if (!activeSessionId) {
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await deleteSession(activeSessionId);
      setStatusText("会话已删除，工作台回到了空白状态。");
      setActiveSessionId(null);
      setMessages([]);
      setStreamingReply("");
      setStreamingChart(null);
      setFinancial(null);
      setComparison(null);
      setReportHtml("");
      setActiveTarget(null);
      setActiveTargets([]);
      setSessionTitleDraft("");
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "删除会话失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendPrompt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (!trimmed || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setStreamingReply("");
    setStreamingChart(null);
    setStatusText("AI 正在通过流式接口返回分析结果...");

    const optimisticMessages = [...messages, { role: "user" as const, content: trimmed }];
    setMessages(optimisticMessages);
    setPrompt("");

    try {
      await sendChatStream(
        {
          prompt: trimmed,
          sessionId: activeSessionId,
          chatHistory: messages,
          activeTarget,
          activeTargets,
        },
        {
          onChunk: (chunk) => {
            setStreamingReply((current) => current + chunk);
          },
          onDone: (done) => {
            setMessages(done.messages);
            setActiveSessionId(done.session_id);
            setActiveTarget(done.active_target ?? null);
            setActiveTargets(done.active_targets ?? []);
            setStreamingReply("");
            setStreamingChart(done.payload.chart ?? null);
            setStatusText("流式分析已完成，结构化 payload 与图表卡片已同步。");
          },
          onError: (message) => {
            setError(message);
          },
        },
      );
      await refreshSessions();
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "发送消息失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateReport() {
    if (!messages.length) {
      setError("请先生成一些对话内容，再导出报告。");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await buildReport(messages, activeTarget);
      setReportHtml(response.html);
      setStatusText("报告已经生成，可以预览或下载 HTML。");
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "报告生成失败");
    } finally {
      setLoading(false);
    }
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

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-card">
          <img src="/assets/logo.png" alt="Logo" className="brand-card__logo" />
          <div className="brand-card__info">
            <h1>光之耀面</h1>
            <span className="brand-card__desc">超清数智决策中心</span>
          </div>
        </div>

        <button className="primary-button" onClick={() => void handleNewSession()} type="button">
          新建会话
        </button>


        <section className="sidebar-section">
          <div className="sidebar-section__header">
            <span className="eyebrow">Sessions</span>
            <strong>{sessions.length}</strong>
          </div>
          <div className="session-list">
            {sessions.map((session) => (
              <button
                key={session.session_id}
                className={`session-pill ${activeSessionId === session.session_id ? "is-active" : ""}`}
                onClick={() => void openSession(session.session_id)}
                type="button"
              >
                <span>{session.title}</span>
                <small>{session.updated_at ?? "刚刚更新"}</small>
              </button>
            ))}
          </div>
        </section>

        {activeSessionId ? (
          <section className="sidebar-section sidebar-actions">
            <span className="eyebrow">Session Actions</span>
            <input
              value={sessionTitleDraft}
              onChange={(event) => setSessionTitleDraft(event.target.value)}
              placeholder="重命名当前会话"
            />
            <div className="sidebar-actions__buttons">
              <button className="secondary-button" onClick={() => void handleRenameSession()} type="button">
                保存标题
              </button>
              <button className="danger-button" onClick={() => void handleDeleteSession()} type="button">
                删除会话
              </button>
            </div>
          </section>
        ) : null}
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <nav className="nav-pills">
            {navItems.map((item) => (
              <button
                key={item.key}
                className={`nav-pill ${nav === item.key ? "is-active" : ""}`}
                onClick={() => setNav(item.key)}
                type="button"
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="topbar__right">
            <span className="eyebrow">Session Info</span>
            <p>{activeSession?.title ?? "新分析会话"} · {loading ? "计算中" : "待命"}</p>
          </div>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        {nav === "chat" ? (
          <section className="content-grid">
            <div className="conversation-panel panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">Conversation</span>
                  <h2>智能研判主控台</h2>
                </div>
                <span className="panel-header__hint">
                  {activeSession?.title ?? "新会话"} · {loading ? "处理中" : "待命"}
                </span>
              </div>

              <div className="chat-timeline">
                {!messages.length && !streamingReply ? (
                  <div className="empty-state">
                    <span className="eyebrow">Starting Point</span>
                    <h3>新前端已经接上结构化对话链路</h3>
                    <p>你现在可以在这里直接对公司发问，后端会通过新的 API 返回文本、图表和会话持久化结果。</p>
                  </div>
                ) : null}

                {messages.map((message, index) => (
                  <article
                    key={`${message.role}-${index}`}
                    className={`message-bubble ${message.role === "user" ? "is-user" : "is-assistant"}`}
                  >
                    <div className="message-bubble__meta">{message.role === "user" ? "USER" : "AI"}</div>
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
                ))}

                {streamingReply ? (
                  <article className="message-bubble is-assistant is-streaming">
                    <div className="message-bubble__meta">AI STREAM</div>
                    <div className="message-bubble__body">
                      {renderFormattedContent(streamingReply)}
                    </div>
                  </article>
                ) : null}
              </div>

              <form className="composer" onSubmit={(event) => void handleSendPrompt(event)}>
                <textarea
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  placeholder="有问题，尽管问"
                  rows={1}
                />
                <button 
                  className="composer-send-button" 
                  disabled={loading || !prompt.trim()} 
                  type="submit"
                  title="发送问题"
                >
                  {loading ? "..." : "↑"}
                </button>
              </form>
            </div>

            <div className="insight-panel panel">
              <div className="panel-header">
                <div>
                  <span className="eyebrow">Analysis Dashboard</span>
                  <h2>辅助研究看板</h2>
                </div>
              </div>

              <div className="insight-panel__scroll">
                <div className="chart-dashboard">
                  {allAssistantCharts.map((chart, idx) => (
                    <EChartCard key={`hist-chart-${idx}`} chart={chart} />
                  ))}
                  {streamingChart ? <EChartCard chart={streamingChart} /> : null}

                  {!allAssistantCharts.length && !streamingChart && (
                    <div className="empty-state compact">
                      <p>等待模型回复产生可视化图表...</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {nav === "financial" ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Financial</span>
                <h2>财务透视面板</h2>
              </div>
              <span className="panel-header__hint">{activeTarget ?? "先从聊天中锁定一个标的"}</span>
            </div>

            {!activeTarget ? (
              <div className="empty-state compact">
                <h3>尚未锁定分析标的</h3>
                <p>先在聊天页发起一次针对公司的提问，这里就会复用新的财务接口结果。</p>
              </div>
            ) : financial?.has_data ? (
              <>
                <div className="overview-strip overview-strip--financial">
                  <StatTile label="数据源" value={financial.source ?? "未知"} />
                  <StatTile label="计量单位" value={financial.unit_hint ?? "-"} />
                  <StatTile label="返回行数" value={financial.rows.length} />
                </div>
                <div className="table-shell">
                  <DataTable rows={financial.rows} />
                </div>
              </>
            ) : (
              <div className="empty-state compact">
                <h3>未取到财务数据</h3>
                <p>{financial?.error ?? "请检查数据源状态，或尝试换一个证券代码。"}</p>
              </div>
            )}
          </section>
        ) : null}

        {nav === "comparison" ? (
          <section className="panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Comparison</span>
                <h2>赛道对标面板</h2>
              </div>
              <span className="panel-header__hint">{comparisonSymbol || "等待标的代码"}</span>
            </div>

            {!comparisonSymbol ? (
              <div className="empty-state compact">
                <h3>还没有可对标的证券代码</h3>
                <p>当前版本会从聊天锁定的标的里提取 6 位股票代码，然后自动拉取对标样本。</p>
              </div>
            ) : (
              <>
                <div className="overview-strip overview-strip--comparison">
                  <StatTile
                    label="赛道模板"
                    value={comparison?.track_template?.track_name ?? "待返回"}
                    tone="accent"
                  />
                  <StatTile label="样本数量" value={comparison?.snapshots.length ?? 0} />
                  <StatTile
                    label="整体覆盖率"
                    value={`${Math.round((comparison?.data_quality?.overall_coverage ?? 0) * 100)}%`}
                  />
                  <StatTile
                    label="评分状态"
                    value={comparison?.scoring?.ok ? "已完成" : "待完善"}
                  />
                </div>

                <div className="comparison-grid">
                  <section className="subpanel">
                    <span className="eyebrow">Track Focus</span>
                    <h3>{comparison?.track_template?.focus ?? "等待赛道说明"}</h3>
                    <p>这一区域承接后端赛道模板，用于告诉前端当前应该重点展示哪些指标。</p>
                  </section>

                  <section className="subpanel">
                    <span className="eyebrow">Metric Coverage</span>
                    <DataTable rows={comparison?.data_quality?.metric_rows ?? []} />
                  </section>

                  {(comparison?.chart_specs ?? []).map((chart) => (
                    <div key={chart.title ?? chart.chart_name} className="subpanel subpanel--full subpanel--chart">
                      <EChartCard chart={chart} />
                    </div>
                  ))}

                  <div className="subpanel subpanel--full">
                    <span className="eyebrow">Snapshots</span>
                    <DataTable rows={comparison?.snapshots ?? []} />
                  </div>

                  <div className="subpanel subpanel--full">
                    <span className="eyebrow">Scoring Output</span>
                    <pre>{JSON.stringify(comparison?.scoring ?? {}, null, 2)}</pre>
                  </div>
                </div>
              </>
            )}
          </section>
        ) : null}

        {nav === "report" ? (
          <section className="panel report-panel">
            <div className="panel-header">
              <div>
                <span className="eyebrow">Report</span>
                <h2>研究报告导出</h2>
              </div>
              <div className="report-actions">
                <button className="secondary-button" disabled={!reportHtml} onClick={handleDownloadReport} type="button">
                  下载 HTML
                </button>
                <button
                  className="primary-button primary-button--inline"
                  disabled={loading}
                  onClick={() => void handleGenerateReport()}
                  type="button"
                >
                  {loading ? "生成中..." : "生成报告"}
                </button>
              </div>
            </div>

            {reportHtml ? (
              <div className="report-frame" dangerouslySetInnerHTML={{ __html: reportHtml }} />
            ) : (
              <div className="empty-state compact">
                <h3>报告尚未生成</h3>
                <p>这里已经接上新的 `/api/report`。下一步可以继续补打印样式、封面页和报告模板切换。</p>
              </div>
            )}
          </section>
        ) : null}
      </main>
    </div>
  );
}
