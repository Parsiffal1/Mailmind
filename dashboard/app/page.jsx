"use client";

import React from "react";
import {
  Check,
  Clock,
  Database,
  FileText,
  Layers,
  Inbox,
  ListChecks,
  Mail,
  MessageSquare,
  Paperclip,
  RefreshCcw,
  Search,
  Settings,
  ShieldCheck,
  X,
} from "lucide-react";

const tabs = [
  { id: "tasks", label: "Tasks", icon: ListChecks },
  { id: "emails", label: "Emails", icon: Inbox },
  { id: "documents", label: "Documents", icon: Paperclip },
  { id: "logs", label: "Logs", icon: Database },
  { id: "settings", label: "Settings", icon: Settings },
];

const demoData = {
  stats: { emails: 42, tasks: 18, open_tasks: 12, high_priority_open: 3 },
  ragStatus: {
    enabled: true,
    email_enabled: true,
    pdf_enabled: true,
    embedding_provider: "local_bge_m3",
    indexed: 4,
    email_bodies: 38,
    pdfs: 6,
    chunks: 126,
    top_k: 4,
  },
  settings: {
    scheduler_enabled: true,
    poll_interval_minutes: 15,
    poll_query: "newer_than:14d",
    poll_limit: 40,
    daily_digest_enabled: true,
    daily_digest_time: "08:00",
    deadline_reminders_enabled: true,
    telegram_notifications_enabled: false,
    llm_provider: "anthropic",
    anthropic_model: "claude-sonnet-4-20250514",
    anthropic_api_key_configured: true,
    telegram_bot_token_configured: false,
    telegram_chat_id_configured: false,
    rag_enabled: true,
    rag_email_enabled: true,
    rag_pdf_enabled: true,
    rag_auto_index: false,
    embedding_provider: "local_bge_m3",
    bge_model: "BAAI/bge-m3",
    voyage_model: "voyage-3.5",
    voyage_api_key_configured: false,
    rag_top_k: 4,
    pii_enabled: true,
    pii_mode: "rehydrated",
    pii_redact_names: true,
    pii_preserve_dates: true,
    pii_redact_logs: true,
  },
  tasks: [
    {
      id: "DEMO-101",
      email_id: "email-demo-1",
      description: "Submit housing verification form",
      priority: "high",
      due_at: "2026-05-22T23:59:00Z",
      sender: "Housing Office <housing@example.edu>",
      subject: "Housing document required before Friday",
      completed: 0,
      requires_reply: 0,
      needs_review: 0,
    },
    {
      id: "DEMO-102",
      email_id: "email-demo-2",
      description: "Reply to advisor about course plan",
      priority: "medium",
      due_at: "2026-05-18T18:00:00Z",
      sender: "Academic Advisor <advisor@example.edu>",
      subject: "Re: Fall course planning",
      completed: 0,
      requires_reply: 1,
      needs_review: 0,
    },
    {
      id: "DEMO-103",
      email_id: "email-demo-3",
      description: "Upload internship onboarding packet",
      priority: "high",
      due_at: "2026-05-20T23:59:00Z",
      sender: "Talent Team <onboarding@example.com>",
      subject: "Onboarding documents due this week",
      completed: 0,
      requires_reply: 0,
      needs_review: 0,
    },
    {
      id: "DEMO-104",
      email_id: "email-demo-4",
      description: "Confirm project meeting time",
      priority: "medium",
      due_at: null,
      sender: "Project Lead <lead@example.org>",
      subject: "Re: Research assistant sync",
      completed: 0,
      requires_reply: 1,
      needs_review: 1,
    },
    {
      id: "DEMO-105",
      email_id: "email-demo-5",
      description: "Review scholarship checklist",
      priority: "low",
      due_at: null,
      sender: "Scholarship Office <aid@example.edu>",
      subject: "Application checklist update",
      completed: 0,
      requires_reply: 0,
      needs_review: 1,
    },
  ],
  emails: [
    { id: "email-demo-1", sender: "Housing Office <housing@example.edu>", subject: "Housing document required before Friday", received_at: "2026-05-13T17:30:00Z", task_count: 1 },
    { id: "email-demo-2", sender: "Academic Advisor <advisor@example.edu>", subject: "Re: Fall course planning", received_at: "2026-05-13T15:20:00Z", task_count: 1 },
    { id: "email-demo-3", sender: "Talent Team <onboarding@example.com>", subject: "Onboarding documents due this week", received_at: "2026-05-12T20:10:00Z", task_count: 1 },
  ],
  attachments: [
    {
      id: "att-demo-1",
      email_id: "email-demo-1",
      filename: "Housing_Verification_Form.pdf",
      mime_type: "application/pdf",
      index_status: "indexed",
      indexed: 1,
      chunk_count: 5,
      sender: "Housing Office <housing@example.edu>",
      subject: "Housing document required before Friday",
      received_at: "2026-05-13T17:30:00Z",
    },
    {
      id: "att-demo-2",
      email_id: "email-demo-3",
      filename: "Internship_Onboarding_Packet.pdf",
      mime_type: "application/pdf",
      index_status: "indexed",
      indexed: 1,
      chunk_count: 8,
      sender: "Talent Team <onboarding@example.com>",
      subject: "Onboarding documents due this week",
      received_at: "2026-05-12T20:10:00Z",
    },
    {
      id: "att-demo-3",
      email_id: "email-demo-5",
      filename: "Scholarship_Checklist.pdf",
      mime_type: "application/pdf",
      index_status: "pending",
      indexed: 0,
      chunk_count: 0,
      sender: "Scholarship Office <aid@example.edu>",
      subject: "Application checklist update",
      received_at: "2026-05-10T16:00:00Z",
    },
  ],
  logs: [
    { id: 1, email_id: "email-demo-1", status: "tasks_created", message: "Created 1 task(s).", created_at: "2026-05-13T17:31:00Z" },
    { id: 2, email_id: "email-demo-1", status: "rag_email_indexed", message: "Email body indexed 4 chunk(s).", created_at: "2026-05-13T17:31:10Z" },
    { id: 3, email_id: null, status: "sync_completed", message: "Processed 3 new email(s). Refreshed extraction for 40 email(s).", created_at: "2026-05-13T17:32:00Z" },
  ],
  selectedEmail: {
    id: "email-demo-1",
    sender: "Housing Office <housing@example.edu>",
    subject: "Housing document required before Friday",
    received_at: "2026-05-13T17:30:00Z",
    body: "Hello,\n\nPlease submit the attached housing verification form by Friday, May 22. The form is required before your housing file can be marked complete.\n\nThank you,\nHousing Office",
    attachments: [
      { id: "att-demo-1", filename: "Housing_Verification_Form.pdf", mime_type: "application/pdf", index_status: "indexed", chunk_count: 5 },
    ],
    tasks: [],
  },
  answer: {
    answer: "Based on the retrieved MailMind sample sources, these items need attention this week:\n\n- **Submit the housing verification form** - the housing office says the attached form is required before the file can be marked complete, with a due date of May 22.\n- **Upload the internship onboarding packet** - the talent team requests signed onboarding documents before the internship setup can continue.\n- **Reply to the academic advisor** - the advisor asks for a preferred fall course plan before the advising meeting.\n\nThe most urgent item is the **housing verification form** because it has a concrete deadline and blocks completion of the housing file. The onboarding packet is also high priority because it is tied to internship setup.",
    sources: [
      {
        attachment_id: "att-demo-1",
        email_id: "email-demo-1",
        filename: "Housing_Verification_Form.pdf",
        page: 1,
        snippet: "Submit the attached housing verification form by Friday, May 22. The form is required before the housing file can be marked complete. Missing documents may delay approval.",
        document_type: "pdf",
        subject: "Housing document required before Friday",
        sender: "Housing Office <housing@example.edu>",
        chunk_type: "PDF",
      },
      {
        attachment_id: "",
        email_id: "email-demo-2",
        filename: "",
        page: 0,
        snippet: "Can you reply with your preferred fall course plan before our advising meeting? Please include the two backup courses you mentioned.",
        document_type: "email",
        subject: "Re: Fall course planning",
        sender: "Academic Advisor <advisor@example.edu>",
        chunk_type: "email_current_message",
      },
      {
        attachment_id: "att-demo-2",
        email_id: "email-demo-3",
        filename: "Internship_Onboarding_Packet.pdf",
        page: 2,
        snippet: "Upload the signed onboarding packet this week so the internship profile, payroll setup, and system access can be prepared before the start date.",
        document_type: "pdf",
        subject: "Onboarding documents due this week",
        sender: "Talent Team <onboarding@example.com>",
        chunk_type: "PDF",
      },
    ],
  },
};

export default function App() {
  const isDemo = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("demo") === "1";
  const [activeTab, setActiveTab] = React.useState("tasks");
  const [tasks, setTasks] = React.useState([]);
  const [emails, setEmails] = React.useState([]);
  const [logs, setLogs] = React.useState([]);
  const [attachments, setAttachments] = React.useState([]);
  const [ragStatus, setRagStatus] = React.useState(null);
  const [stats, setStats] = React.useState(null);
  const [settings, setSettings] = React.useState(null);
  const [selectedTaskId, setSelectedTaskId] = React.useState(null);
  const [selectedEmail, setSelectedEmail] = React.useState(null);
  const [emailLoading, setEmailLoading] = React.useState(false);
  const [readerOpen, setReaderOpen] = React.useState(false);
  const [sortMode, setSortMode] = React.useState("newest");
  const [filters, setFilters] = React.useState({
    reply_thread: false,
    has_attachments: false,
    needs_review: false,
    due_only: false,
  });
  const [query, setQuery] = React.useState("");
  const [aiQuestion, setAiQuestion] = React.useState("");
  const [aiAnswer, setAiAnswer] = React.useState(null);
  const [aiLoading, setAiLoading] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [message, setMessage] = React.useState("");
  const aiAbortRef = React.useRef(null);

  const refresh = React.useCallback(async (options = {}) => {
    if (isDemo) {
      setTasks(demoData.tasks);
      setEmails(demoData.emails);
      setLogs(demoData.logs);
      setStats(demoData.stats);
      setAttachments(demoData.attachments);
      setRagStatus(demoData.ragStatus);
      setSettings(demoData.settings);
      setSelectedEmail(demoData.selectedEmail);
      setLoading(false);
      return;
    }
    const clearMessage = options.clearMessage ?? true;
    setLoading(true);
    if (clearMessage) {
      setMessage("");
    }
    try {
      const params = new URLSearchParams();
      params.set("sort", sortMode);
      if (query) params.set("search", query);
      Object.entries(filters).forEach(([key, value]) => {
        if (value) params.set(key, "true");
      });
      const [tasksRes, emailsRes, logsRes, statsRes] = await Promise.all([
        fetch(`/api/tasks?${params.toString()}`),
        fetch("/api/emails"),
        fetch("/api/logs?limit=50"),
        fetch("/api/stats"),
      ]);
      const [attachmentsRes, ragStatusRes] = await Promise.all([
        fetch("/api/attachments"),
        fetch("/api/rag/status"),
      ]);
      setTasks(await tasksRes.json());
      setEmails(await emailsRes.json());
      setLogs(await logsRes.json());
      setStats(await statsRes.json());
      setAttachments(await attachmentsRes.json());
      setRagStatus(await ragStatusRes.json());
      if (!settings) {
        const settingsRes = await fetch("/api/settings");
        setSettings(await settingsRes.json());
      }
    } catch (error) {
      setMessage(`Refresh failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  }, [isDemo, query, settings, sortMode, filters]);

  async function syncMailMind() {
    if (isDemo) {
      setMessage("Demo refresh complete: sample Gmail data, tasks, and AI search index loaded.");
      refresh({ clearMessage: false });
      return;
    }
    setLoading(true);
    setMessage("Refreshing MailMind: Gmail, task extraction, AI search index, and dashboard...");
    try {
      const response = await fetch("/api/sync", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Sync failed");
      }
      const rag = payload.rag || {};
      const extraction = payload.extraction || {};
      setMessage(
        `Refresh complete: ${payload.emails_processed ?? 0} new email(s), ${extraction.refreshed ?? 0} email(s) re-extracted, ${rag.emails?.indexed ?? 0} email body/bodies indexed, ${rag.pdfs?.indexed ?? 0} PDF(s) indexed, ${rag.failed ?? 0} failed.`
      );
      await refresh({ clearMessage: false });
    } catch (error) {
      setMessage(`Sync failed: ${error.message}`);
      setLoading(false);
    }
  }

  React.useEffect(() => {
    refresh();
  }, [refresh]);

  const selectedTask = React.useMemo(() => {
    if (!tasks.length) {
      return null;
    }
    return tasks.find((task) => task.id === selectedTaskId) ?? tasks[0];
  }, [selectedTaskId, tasks]);

  React.useEffect(() => {
    if (!selectedTask?.email_id) {
      setSelectedEmail(null);
      return;
    }
    if (isDemo) {
      setSelectedEmail(demoData.selectedEmail);
      setEmailLoading(false);
      return;
    }
    let cancelled = false;
    setEmailLoading(true);
    fetch(`/api/emails/${selectedTask.email_id}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Could not load email detail");
        }
        return response.json();
      })
      .then((payload) => {
        if (!cancelled) {
          setSelectedEmail(payload);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setSelectedEmail({ body_fetch_error: error.message });
        }
      })
      .finally(() => {
        if (!cancelled) {
          setEmailLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [isDemo, selectedTask?.email_id]);

  async function markDone(taskId) {
    if (isDemo) {
      setMessage(`Demo mode: task ${taskId} marked complete locally.`);
      return;
    }
    setMessage("");
    const response = await fetch(`/api/tasks/${taskId}/done`, { method: "PATCH" });
    if (!response.ok) {
      setMessage(`Could not complete task ${taskId}`);
      return;
    }
    setMessage(`Completed task ${taskId}`);
    refresh();
  }

  async function indexPdfAttachments() {
    if (isDemo) {
      setMessage("Demo mode: indexed 38 email bodies and 2 PDF files from sample data.");
      setActiveTab("documents");
      return;
    }
    setLoading(true);
    setMessage("Rebuilding AI search index...");
    try {
      const response = await fetch("/api/rag/index?rebuild=true", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Indexing failed");
      }
      setMessage(
        `Indexed ${payload.emails?.indexed ?? 0} email(s) and ${payload.pdfs?.indexed ?? 0} PDF(s) from enabled sources, skipped ${payload.skipped}, failed ${payload.failed}.`
      );
      await refresh();
      setActiveTab("documents");
    } catch (error) {
      setMessage(`Indexing failed: ${error.message}`);
      setLoading(false);
    }
  }

  async function askIndexedDocuments(event) {
    event.preventDefault();
    if (!aiQuestion.trim()) {
      return;
    }
    if (isDemo) {
      setAiLoading(true);
      setMessage("");
      await new Promise((resolve) => setTimeout(resolve, 450));
      setAiAnswer(demoData.answer);
      setAiLoading(false);
      setActiveTab("documents");
      return;
    }
    if (aiAbortRef.current) {
      aiAbortRef.current.abort();
    }
    const controller = new AbortController();
    aiAbortRef.current = controller;
    setAiLoading(true);
    setMessage("");
    try {
      const response = await fetch("/api/rag/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: aiQuestion }),
        signal: controller.signal,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Question failed");
      }
      setAiAnswer(payload);
      setActiveTab("documents");
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      setAiAnswer(null);
      setMessage(`AI search failed: ${error.message}`);
    } finally {
      if (aiAbortRef.current === controller) {
        aiAbortRef.current = null;
        setAiLoading(false);
      }
    }
  }

  function clearAiSearch() {
    if (aiAbortRef.current) {
      aiAbortRef.current.abort();
      aiAbortRef.current = null;
    }
    setAiQuestion("");
    setAiAnswer(null);
    setAiLoading(false);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">
            <img src="/mailmind-logo.svg" alt="MailMind logo" />
          </div>
          <div>
            <h1>MailMind</h1>
            <p>Gmail task intelligence</p>
          </div>
        </div>
        <nav className="sideNav" aria-label="Primary">
          <SideNavItem icon={ListChecks} label="Tasks" active={activeTab === "tasks"} onClick={() => setActiveTab("tasks")} />
          <SideNavItem icon={Inbox} label="Emails" active={activeTab === "emails"} onClick={() => setActiveTab("emails")} />
          <SideNavItem icon={Paperclip} label="Documents" active={activeTab === "documents"} onClick={() => setActiveTab("documents")} />
          <SideNavItem icon={Database} label="Logs" active={activeTab === "logs"} onClick={() => setActiveTab("logs")} />
          <SideNavItem icon={Settings} label="Settings" active={activeTab === "settings"} onClick={() => setActiveTab("settings")} />
        </nav>
        <div className="localMode">
          <ShieldCheck size={18} />
          <div>
            <strong>Local-first mode</strong>
            <span>SQLite + Gmail readonly</span>
          </div>
        </div>
      </aside>

      <main className="mainShell">
        <header className="topbar compactTopbar">
          <div className="actions">
            <button className="primaryButton" onClick={syncMailMind} disabled={loading} title="Refresh Gmail, re-extract tasks, update AI search, and reload the dashboard">
              <RefreshCcw size={18} />
              <span>Refresh</span>
            </button>
          </div>
        </header>

        <AiSearchBar
          question={aiQuestion}
          setQuestion={setAiQuestion}
          clearSearch={clearAiSearch}
          answer={aiAnswer}
          asking={aiLoading}
          loading={loading}
          ragStatus={ragStatus}
          onAsk={askIndexedDocuments}
          onIndex={indexPdfAttachments}
        />

        <section className="summaryBand" aria-label="Mailbox summary">
          <Metric icon={Inbox} label="Emails" value={stats?.emails ?? "-"} />
          <Metric icon={ListChecks} label="Open tasks" value={stats?.open_tasks ?? "-"} />
          <Metric icon={Clock} label="All tasks" value={stats?.tasks ?? "-"} />
          <Metric icon={Database} label="High priority" value={stats?.high_priority_open ?? "-"} />
        </section>

        <section className="workspaceGrid">
          <div className="workspace">
          <div className="tabs" role="tablist" aria-label="Dashboard views">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  className={activeTab === tab.id ? "tab active" : "tab"}
                  onClick={() => setActiveTab(tab.id)}
                  role="tab"
                  aria-selected={activeTab === tab.id}
                >
                  <Icon size={17} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          {message && <div className="statusLine">{message}</div>}

          {activeTab === "tasks" && (
            <TasksView
              tasks={tasks}
              selectedTask={selectedTask}
              setSelectedTaskId={setSelectedTaskId}
              query={query}
              setQuery={setQuery}
              sortMode={sortMode}
              setSortMode={setSortMode}
              filters={filters}
              setFilters={setFilters}
              refresh={refresh}
              markDone={markDone}
              loading={loading}
            />
          )}
          {activeTab === "emails" && <EmailsView emails={emails} />}
          {activeTab === "documents" && (
            <DocumentsView
              attachments={attachments}
              ragStatus={ragStatus}
              refresh={refresh}
              setMessage={setMessage}
              loading={loading}
              setLoading={setLoading}
              onIndexAll={indexPdfAttachments}
            />
          )}
          {activeTab === "logs" && <LogsView logs={logs} />}
          {activeTab === "settings" && (
            <SettingsView settings={settings} setSettings={setSettings} setMessage={setMessage} />
          )}
          </div>
          <DetailPanel
            task={selectedTask}
            email={selectedEmail}
            emailLoading={emailLoading}
            stats={stats}
            openReader={() => setReaderOpen(true)}
          />
        </section>
      </main>
      {readerOpen && (
        <EmailReaderModal
          task={selectedTask}
          email={selectedEmail}
          emailLoading={emailLoading}
          onClose={() => setReaderOpen(false)}
        />
      )}
    </div>
  );
}

function SideNavItem({ icon: Icon, label, active = false, disabled = false, onClick }) {
  return (
    <button className={active ? "sideNavItem active" : "sideNavItem"} disabled={disabled} onClick={onClick}>
      <Icon size={18} />
      <span>{label}</span>
    </button>
  );
}

function Metric({ icon: Icon, label, value }) {
  return (
    <div className="metric">
      <Icon size={18} />
      <div>
        <div className="metricValue">{value}</div>
        <div className="metricLabel">{label}</div>
      </div>
    </div>
  );
}

function cleanRagText(value) {
  return String(value || "")
    .replace(/[\u0000-\u001f\u007f-\u009f]/g, " ")
    .replace(/\uFFFD/g, "")
    .replace(/_{5,}/g, "____")
    .replace(/\s+/g, " ")
    .trim();
}

function renderInlineMarkdown(text) {
  const parts = String(text || "").split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={index}>{part.slice(1, -1)}</code>;
    }
    return part;
  });
}

function MarkdownBlock({ text }) {
  const lines = String(text || "").split(/\r?\n/);
  const blocks = [];
  let listItems = [];

  const flushList = () => {
    if (!listItems.length) return;
    blocks.push(
      <ul key={`list-${blocks.length}`}>
        {listItems.map((item, index) => (
          <li key={index}>{renderInlineMarkdown(item)}</li>
        ))}
      </ul>
    );
    listItems = [];
  };

  lines.forEach((rawLine) => {
    const line = rawLine.trim();
    if (!line) {
      flushList();
      return;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    const bullet = line.match(/^[-*]\s+(.+)$/);
    const numbered = line.match(/^\d+\.\s+(.+)$/);
    if (heading) {
      flushList();
      blocks.push(<h4 key={`h-${blocks.length}`}>{renderInlineMarkdown(heading[2])}</h4>);
      return;
    }
    if (bullet || numbered) {
      listItems.push((bullet || numbered)[1]);
      return;
    }
    flushList();
    blocks.push(<p key={`p-${blocks.length}`}>{renderInlineMarkdown(line)}</p>);
  });
  flushList();

  return <div className="markdownBody">{blocks}</div>;
}

function AiSearchBar({ question, setQuestion, clearSearch, answer, asking, loading, ragStatus, onAsk, onIndex }) {
  const steps = [
    "Parsing request",
    "Searching MailMind data",
    "Reading sources",
    "Synthesizing answer",
  ];
  const examples = [
    "Find urgent emails from this week",
    "Summarize tasks with attachments",
    "What should I reply to next?",
    "Search deadlines across Gmail",
  ];
  return (
    <section className={answer ? "aiSearchSection compact hasAnswer" : "aiSearchSection compact"} aria-label="AI search">
      <div className="ambientBlob blobA" />
      <div className="ambientBlob blobB" />
      <div className="ambientBlob blobC" />
      <form className="aiSearchBar" onSubmit={onAsk}>
        <div className="aiSearchIcon">
          <Search size={18} />
        </div>
        <div className={question ? "aiInputWrap hasValue" : "aiInputWrap"}>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            aria-label="Search anything with AI"
          />
          {question && (
            <button
              className="aiClearButton"
              type="button"
              onClick={clearSearch}
              aria-label="Clear AI search"
            >
              <X size={14} />
            </button>
          )}
          <div className="aiInlinePrompt" aria-hidden="true">
            <span className="promptLead">Search anything with AI</span>
            <span className="promptTicker">
              {examples.map((example) => (
                <span key={example}>{example}</span>
              ))}
            </span>
          </div>
        </div>
        <div className="aiSearchStatus">
          <span>{ragStatus?.embedding_provider === "local_bge_m3" ? "Local BGE-M3" : "Vector"}</span>
          <strong>{(ragStatus?.indexed ?? 0) + (ragStatus?.email_bodies ?? 0)} indexed</strong>
        </div>
        <button className="aiGhostButton" type="button" onClick={onIndex} disabled={loading || !ragStatus?.enabled}>
          <Paperclip size={15} />
          <span>Index sources</span>
        </button>
        <button className={asking ? "aiSubmitButton asking" : "aiSubmitButton"} type="submit" disabled={asking || !ragStatus?.enabled}>
          <MessageSquare size={15} />
          <span>{asking ? "Thinking" : "Ask AI"}</span>
        </button>
      </form>

      {(asking || answer) && (
        <div className="searchStatusRail" aria-label="AI search status">
          {steps.map((step, index) => (
            <div
              className={
                asking
                  ? index === 3
                    ? "statusStep active"
                    : "statusStep done"
                  : "statusStep done"
              }
              key={step}
            >
              <span />
              {step}
            </div>
          ))}
        </div>
      )}

      {asking && (
        <div className="aiAnswerPanel loadingPanel" aria-live="polite">
          <div className="aiAnswerText">
            <h3>Reading indexed sources</h3>
            <div className="skeletonLine wide" />
            <div className="skeletonLine" />
            <div className="skeletonLine short" />
          </div>
          <div className="aiSourceStrip">
            {[0, 1, 2].map((item) => (
              <div className="sourceSkeleton" key={item} />
            ))}
          </div>
        </div>
      )}

      {!asking && answer && (
        <div className="aiAnswerPanel">
          <div className="aiAnswerText">
            <h3>Answer</h3>
            <MarkdownBlock text={answer.answer} />
          </div>
          <div className="aiSourceStrip">
            {answer.sources?.length ? (
              answer.sources.slice(0, 3).map((source, index) => {
                const isEmail = source.document_type === "email";
                const filename = cleanRagText(isEmail ? source.subject || source.filename : source.filename) || "Indexed document";
                const subject = cleanRagText(source.subject) || "Source email";
                const snippet = cleanRagText(source.snippet);
                return (
                  <article className="aiSourceCard" style={{ "--delay": `${index * 70}ms` }} key={`${source.attachment_id}-${source.page}-${index}`}>
                    <div className="sourceCardTop">
                      <strong>{filename}</strong>
                      <span>{isEmail ? (source.chunk_type || "Email") : `Page ${source.page || "?"}`}</span>
                    </div>
                    <span className="sourceSubject">{subject}</span>
                    {snippet && <p>{snippet}</p>}
                  </article>
                );
              })
            ) : (
              <span>No source citations returned.</span>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function TasksView({
  tasks,
  selectedTask,
  setSelectedTaskId,
  query,
  setQuery,
  sortMode,
  setSortMode,
  filters,
  setFilters,
  refresh,
  markDone,
  loading,
}) {
  const activeFilterCount = Object.values(filters).filter(Boolean).length;
  function toggleFilter(key) {
    setFilters((current) => ({ ...current, [key]: !current[key] }));
  }
  function clearFilters() {
    setFilters({ reply_thread: false, has_attachments: false, needs_review: false, due_only: false });
  }
  return (
    <div className="panel">
      <div className="panelHeader">
        <div>
          <h2>Open Tasks</h2>
          <p>LLM-extracted actions from Gmail, sorted by deadline.</p>
        </div>
        <form
          className="search"
          onSubmit={(event) => {
            event.preventDefault();
            refresh();
          }}
        >
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search tasks"
            aria-label="Search tasks"
          />
        </form>
        <label className="sortControl">
          <span>Sort</span>
          <select value={sortMode} onChange={(event) => setSortMode(event.target.value)}>
            <option value="newest">Newest email</option>
            <option value="priority">Priority</option>
            <option value="due">Due date</option>
            <option value="oldest">Oldest email</option>
          </select>
        </label>
      </div>
      <div className="filterBar">
        <span className="filterLabel">Filters</span>
        <FilterChip active={filters.reply_thread} onClick={() => toggleFilter("reply_thread")}>
          Reply thread
        </FilterChip>
        <FilterChip active={filters.has_attachments} onClick={() => toggleFilter("has_attachments")}>
          Has attachments
        </FilterChip>
        <FilterChip active={filters.needs_review} onClick={() => toggleFilter("needs_review")}>
          Needs review
        </FilterChip>
        <FilterChip active={filters.due_only} onClick={() => toggleFilter("due_only")}>
          Has deadline
        </FilterChip>
        {activeFilterCount > 0 && (
          <button className="clearFilters" onClick={clearFilters}>
            Clear
          </button>
        )}
      </div>
      <div className="tableWrap">
        <table>
          <thead>
            <tr>
              <th>Task</th>
              <th>Priority</th>
              <th>Due</th>
              <th>Source</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {tasks.length === 0 ? (
              <tr>
                <td colSpan="5" className="empty">
                  {loading ? "Loading tasks..." : "No open tasks."}
                </td>
              </tr>
            ) : (
              tasks.map((task) => (
                <tr
                  key={task.id}
                  className={selectedTask?.id === task.id ? "selectedRow" : ""}
                  onClick={() => setSelectedTaskId(task.id)}
                >
                  <td>
                    <div className="taskTitle">{task.description}</div>
                    {Boolean(task.needs_review) && <div className="tag">Needs review</div>}
                  </td>
                  <td>
                    <span className={`priority ${task.priority}`}>{task.priority}</span>
                  </td>
                  <td>{formatDate(task.due_at)}</td>
                  <td>
                    <div className="sender">{task.sender}</div>
                    <div className="subject">{task.subject}</div>
                  </td>
                  <td>
                    <button
                      className="doneButton"
                      onClick={(event) => {
                        event.stopPropagation();
                        markDone(task.id);
                      }}
                      title="Mark complete"
                    >
                      <Check size={17} />
                      <span>Done</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function FilterChip({ active, onClick, children }) {
  return (
    <button className={active ? "filterChip active" : "filterChip"} onClick={onClick}>
      {children}
    </button>
  );
}

function DetailPanel({ task, email, emailLoading, stats, openReader }) {
  return (
    <aside className="detailPanel">
      <div>
        <p className="eyebrow">Task detail</p>
        <h2>{task ? "Selected action" : "No task selected"}</h2>
      </div>
      {task ? (
        <>
          <div className="detailCard">
            <div className="detailIcon">
              <FileText size={18} />
            </div>
            <h3>{task.description}</h3>
            <div className="detailMeta">
              <span>Priority: {task.priority}</span>
              <span>Due: {formatDate(task.due_at)}</span>
              <span>Requires reply: {task.requires_reply ? "yes" : "no"}</span>
              <span>Review flag: {task.needs_review ? "yes" : "no"}</span>
            </div>
          </div>
          <div className="sourceBox">
            <Mail size={18} />
            <div>
              <strong>{task.subject || "No subject"}</strong>
              <span>{task.sender}</span>
            </div>
          </div>
          <button className="readerButton" onClick={openReader} disabled={emailLoading}>
            <Mail size={17} />
            <span>{emailLoading ? "Loading email" : "Open full email"}</span>
          </button>
          <div className="attachmentsBox">
            <h3>Attachments</h3>
            {email?.attachments?.length ? (
              email.attachments.map((attachment) => {
                const status = attachment.index_status || (attachment.indexed ? "indexed" : "pending");
                return (
                  <span key={attachment.id}>
                    {attachment.filename}
                    <small>{status}{attachment.chunk_count ? ` · ${attachment.chunk_count} chunks` : ""}</small>
                  </span>
                );
              })
            ) : (
              <span>No attachments indexed</span>
            )}
          </div>
        </>
      ) : (
        <div className="detailCard emptyDetail">Run Gmail polling or clear your search to select a task.</div>
      )}
      <div className="pipelineBox">
        <h3>Pipeline health</h3>
        <div className="healthRow">
          <span>Gmail OAuth</span>
          <strong>Connected</strong>
        </div>
        <div className="healthRow">
          <span>LLM extraction</span>
          <strong>Active</strong>
        </div>
        <div className="healthRow">
          <span>Open tasks</span>
          <strong>{stats?.open_tasks ?? "-"}</strong>
        </div>
      </div>
    </aside>
  );
}

function EmailReaderModal({ task, email, emailLoading, onClose }) {
  return (
    <div className="modalLayer" role="dialog" aria-modal="true" aria-label="Full email reader">
      <div className="emailReader">
        <div className="readerHeader">
          <div>
            <p className="eyebrow">Source email</p>
            <h2>{email?.subject || task?.subject || "No subject"}</h2>
            <p>{email?.sender || task?.sender}</p>
          </div>
          <button className="closeButton" onClick={onClose} title="Close reader">
            <X size={18} />
          </button>
        </div>

        {task && (
          <div className="readerTaskBanner">
            <span>Extracted task</span>
            <strong>{task.description}</strong>
          </div>
        )}

        <div className="readerBody">
          {email?.body_fetch_error ? (
            <p className="emailError">{email.body_fetch_error}</p>
          ) : (
            <pre>{emailLoading ? "Loading full email body..." : email?.body || "No email body saved yet."}</pre>
          )}
        </div>

        <div className="readerFooter">
          <span>{email?.received_at ? `Received ${formatDate(email.received_at)}` : "Received date unavailable"}</span>
          <span>{email?.attachments?.length ? `${email.attachments.length} attachment(s)` : "No attachments"}</span>
        </div>
      </div>
    </div>
  );
}

function DocumentsView({ attachments, ragStatus, refresh, setMessage, loading, setLoading, onIndexAll }) {
  const [docQuery, setDocQuery] = React.useState("");
  const [statusFilter, setStatusFilter] = React.useState("all");

  const pdfAttachments = React.useMemo(() => {
    return attachments.filter((attachment) => {
      const filename = attachment.filename || "";
      const mime = attachment.mime_type || "";
      return filename.toLowerCase().endsWith(".pdf") || mime.toLowerCase() === "application/pdf";
    });
  }, [attachments]);

  const filtered = React.useMemo(() => {
    return pdfAttachments.filter((attachment) => {
      const haystack = `${attachment.filename || ""} ${attachment.subject || ""} ${attachment.sender || ""}`.toLowerCase();
      const matchesQuery = !docQuery || haystack.includes(docQuery.toLowerCase());
      const status = attachment.index_status || (attachment.indexed ? "indexed" : "pending");
      const matchesStatus = statusFilter === "all" || status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [pdfAttachments, docQuery, statusFilter]);

  async function indexOne(id) {
    setLoading(true);
    setMessage("Indexing selected PDF...");
    try {
      const response = await fetch(`/api/attachments/${id}/index`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Indexing failed");
      }
      setMessage(`${payload.status}: ${payload.chunks} chunk(s).${payload.error ? ` ${payload.error}` : ""}`);
      await refresh();
    } catch (error) {
      setMessage(`Indexing failed: ${error.message}`);
      setLoading(false);
    }
  }

  return (
    <div className="documentsPanel">
      <div className="documentMetrics" aria-label="RAG summary">
        <Metric icon={Paperclip} label="PDF source" value={ragStatus?.pdf_enabled ? (ragStatus?.pdfs ?? pdfAttachments.length) : "Off"} />
        <Metric icon={Mail} label="Email source" value={ragStatus?.email_enabled ? (ragStatus?.email_bodies ?? "-") : "Off"} />
        <Metric icon={Layers} label="Chunks" value={ragStatus?.chunks ?? "-"} />
        <Metric icon={MessageSquare} label="RAG" value={ragStatus?.enabled ? "On" : "Off"} />
      </div>

      <div className="documentsGrid singleColumn">
        <section className="panel documentsListPanel">
          <div className="panelHeader">
            <div>
              <h2>Indexed Sources</h2>
              <p>Index enabled MailMind sources, then ask grounded questions with source citations.</p>
            </div>
            <button
              className="primaryButton"
              onClick={onIndexAll}
              disabled={loading || !ragStatus?.enabled || (!ragStatus?.email_enabled && !ragStatus?.pdf_enabled)}
            >
              <Paperclip size={17} />
              <span>Index enabled sources</span>
            </button>
          </div>
          <div className="documentToolbar">
            <form
              className="search"
              onSubmit={(event) => {
                event.preventDefault();
              }}
            >
              <Search size={17} />
              <input
                value={docQuery}
                onChange={(event) => setDocQuery(event.target.value)}
                placeholder="Search documents"
                aria-label="Search documents"
              />
            </form>
            <div className="filterBar inlineFilters">
              {["all", "indexed", "pending", "skipped", "failed"].map((status) => (
                <FilterChip key={status} active={statusFilter === status} onClick={() => setStatusFilter(status)}>
                  {status}
                </FilterChip>
              ))}
            </div>
          </div>
          <div className="tableWrap">
            <table className="documentsTable">
              <thead>
                <tr>
                  <th>File</th>
                  <th>Source</th>
                  <th>Status</th>
                  <th>Chunks</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="empty">
                      No PDF attachments found. Poll Gmail first, or check your Gmail query limit.
                    </td>
                  </tr>
                ) : (
                  filtered.map((attachment) => {
                    const status = attachment.index_status || (attachment.indexed ? "indexed" : "pending");
                    return (
                      <tr key={attachment.id}>
                        <td>
                          <div className="taskTitle">{attachment.filename}</div>
                          {attachment.index_error && <div className="tag">{attachment.index_error}</div>}
                        </td>
                        <td>
                          <div className="sender">{attachment.sender}</div>
                          <div className="subject">{attachment.subject}</div>
                        </td>
                        <td>
                          <span className={`indexStatus ${status}`}>{status}</span>
                        </td>
                        <td>{attachment.chunk_count ?? "-"}</td>
                        <td>
                          <button className="doneButton" onClick={() => indexOne(attachment.id)} disabled={loading || !ragStatus?.enabled}>
                            <RefreshCcw size={17} />
                            <span>{status === "indexed" ? "Re-index" : "Index"}</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}

function EmailsView({ emails }) {
  return (
    <div className="panel">
      <div className="panelHeader">
        <div>
          <h2>Processed Emails</h2>
          <p>Messages saved locally after Gmail polling.</p>
        </div>
      </div>
      <div className="list">
        {emails.map((email) => (
          <article className="item" key={email.id}>
            <div>
              <h3>{email.subject || "No subject"}</h3>
              <p>{email.sender}</p>
            </div>
            <div className="itemMeta">
              <span>{email.task_count} task(s)</span>
              <span>{formatDate(email.received_at)}</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function LogsView({ logs }) {
  return (
    <div className="panel">
      <div className="panelHeader">
        <div>
          <h2>Processing Log</h2>
          <p>Recent extraction and pipeline events.</p>
        </div>
      </div>
      <div className="list">
        {logs.map((log) => (
          <article className="item" key={log.id}>
            <div>
              <h3>{log.status}</h3>
              <p>{log.message || "No message"}</p>
            </div>
            <div className="itemMeta">
              <span>{log.email_id || "system"}</span>
              <span>{formatDate(log.created_at)}</span>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function SettingsView({ settings, setSettings, setMessage }) {
  const [form, setForm] = React.useState(null);
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (settings && !form) {
      setForm({
        scheduler_enabled: settings.scheduler_enabled,
        poll_interval_minutes: settings.poll_interval_minutes,
        poll_query: settings.poll_query,
        poll_limit: settings.poll_limit,
        daily_digest_enabled: settings.daily_digest_enabled,
        daily_digest_time: settings.daily_digest_time,
        deadline_reminders_enabled: settings.deadline_reminders_enabled,
        telegram_notifications_enabled: settings.telegram_notifications_enabled,
        llm_provider: settings.llm_provider,
        anthropic_model: settings.anthropic_model,
        anthropic_api_key: "",
        telegram_bot_token: "",
        telegram_chat_id: "",
        rag_enabled: settings.rag_enabled,
        rag_email_enabled: settings.rag_email_enabled,
        rag_pdf_enabled: settings.rag_pdf_enabled,
        rag_auto_index: settings.rag_auto_index,
        embedding_provider: settings.embedding_provider,
        bge_model: settings.bge_model,
        voyage_model: settings.voyage_model,
        voyage_api_key: "",
        rag_top_k: settings.rag_top_k,
        pii_enabled: settings.pii_enabled,
        pii_mode: settings.pii_enabled ? settings.pii_mode : "off",
        pii_redact_names: settings.pii_redact_names,
        pii_preserve_dates: settings.pii_preserve_dates,
        pii_redact_logs: settings.pii_redact_logs,
      });
    }
  }, [settings, form]);

  if (!form) {
    return <div className="panel settingsPanel"><div className="empty">Loading settings...</div></div>;
  }

  function setField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      const response = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Settings save failed");
      }
      setSettings(payload.settings);
      setForm((current) => ({
        ...current,
        anthropic_api_key: "",
        telegram_bot_token: "",
        telegram_chat_id: "",
        voyage_api_key: "",
      }));
      setMessage("Settings saved to .env. Restart the worker for scheduler changes to take effect.");
    } catch (error) {
      setMessage(error.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="panel settingsPanel" onSubmit={save}>
      <div className="panelHeader">
        <div>
          <h2>Settings</h2>
          <p>Configure local runtime, LLM credentials, and optional Telegram notifications.</p>
        </div>
        <button className="primaryButton" type="submit" disabled={saving}>
          <Check size={17} />
          <span>{saving ? "Saving" : "Save to .env"}</span>
        </button>
      </div>

      <div className="settingsGrid">
        <section className="settingsSection">
          <h3>Scheduler</h3>
          <Toggle
            label="Enable scheduled worker"
            checked={form.scheduler_enabled}
            onChange={(value) => setField("scheduler_enabled", value)}
          />
          <label className="field">
            <span>Poll interval minutes</span>
            <input
              type="number"
              min="1"
              max="1440"
              value={form.poll_interval_minutes}
              onChange={(event) => setField("poll_interval_minutes", Number(event.target.value))}
              disabled={!form.scheduler_enabled}
            />
          </label>
          <label className="field">
            <span>Gmail query</span>
            <input
              value={form.poll_query}
              onChange={(event) => setField("poll_query", event.target.value)}
            />
          </label>
          <label className="field">
            <span>Poll limit</span>
            <input
              type="number"
              min="1"
              max="100"
              value={form.poll_limit}
              onChange={(event) => setField("poll_limit", Number(event.target.value))}
            />
          </label>
        </section>

        <section className="settingsSection">
          <h3>Reminder jobs</h3>
          <Toggle
            label="Daily deadline digest"
            checked={form.daily_digest_enabled}
            onChange={(value) => setField("daily_digest_enabled", value)}
          />
          <label className="field">
            <span>Daily digest time</span>
            <input
              type="time"
              value={form.daily_digest_time}
              onChange={(event) => setField("daily_digest_time", event.target.value)}
              disabled={!form.daily_digest_enabled}
            />
          </label>
          <Toggle
            label="24-hour deadline warning"
            checked={form.deadline_reminders_enabled}
            onChange={(value) => setField("deadline_reminders_enabled", value)}
          />
        </section>

        <section className="settingsSection">
          <h3>LLM extraction</h3>
          <label className="field">
            <span>Provider</span>
            <select value={form.llm_provider} onChange={(event) => setField("llm_provider", event.target.value)}>
              <option value="anthropic">Anthropic</option>
              <option value="mock">Mock offline</option>
            </select>
          </label>
          <label className="field">
            <span>Anthropic model</span>
            <input value={form.anthropic_model} onChange={(event) => setField("anthropic_model", event.target.value)} />
          </label>
          <label className="field">
            <span>Anthropic API key {settings?.anthropic_api_key_configured ? "(configured)" : "(missing)"}</span>
            <input
              type="password"
              value={form.anthropic_api_key}
              placeholder="Leave blank to keep current key"
              onChange={(event) => setField("anthropic_api_key", event.target.value)}
            />
          </label>
        </section>

        <section className="settingsSection">
          <h3>PII Guard</h3>
          <label className="field">
            <span>Privacy mode</span>
            <select
              value={form.pii_mode}
              onChange={(event) => {
                const mode = event.target.value;
                setForm((current) => ({ ...current, pii_mode: mode, pii_enabled: mode !== "off" }));
              }}
            >
              <option value="off">Off - Claude sees original text</option>
              <option value="rehydrated">Rehydrated - Claude sees placeholders</option>
            </select>
          </label>
          <Toggle
            label="Redact person names"
            checked={form.pii_redact_names}
            onChange={(value) => setField("pii_redact_names", value)}
            disabled={form.pii_mode === "off"}
          />
          <Toggle
            label="Preserve dates for deadline extraction"
            checked={form.pii_preserve_dates}
            onChange={(value) => setField("pii_preserve_dates", value)}
            disabled={form.pii_mode === "off"}
          />
          <Toggle
            label="Redact sensitive values in processing logs"
            checked={form.pii_redact_logs}
            onChange={(value) => setField("pii_redact_logs", value)}
            disabled={form.pii_mode === "off"}
          />
          <p className="settingsHint">
            Off sends original text to Claude. Rehydrated mode sends placeholders such as [PERSON_1] to Claude, then restores the final answer locally for readability. Local email bodies, SQLite rows, and the search index stay original.
          </p>
        </section>

        <section className="settingsSection">
          <h3>Telegram push</h3>
          <Toggle
            label="Enable Telegram notifications"
            checked={form.telegram_notifications_enabled}
            onChange={(value) => setField("telegram_notifications_enabled", value)}
          />
          <label className="field">
            <span>Bot token {settings?.telegram_bot_token_configured ? "(configured)" : "(missing)"}</span>
            <input
              type="password"
              value={form.telegram_bot_token}
              placeholder="Required before enabling push"
              onChange={(event) => setField("telegram_bot_token", event.target.value)}
            />
          </label>
          <label className="field">
            <span>Chat ID {settings?.telegram_chat_id_configured ? "(configured)" : "(missing)"}</span>
            <input
              value={form.telegram_chat_id}
              placeholder="Required before enabling push"
              onChange={(event) => setField("telegram_chat_id", event.target.value)}
            />
          </label>
        </section>

        <section className="settingsSection">
          <h3>AI Search Sources</h3>
          <Toggle
            label="Enable AI search / RAG"
            checked={form.rag_enabled}
            onChange={(value) => setField("rag_enabled", value)}
          />
          <Toggle
            label="Include Gmail email bodies"
            checked={form.rag_email_enabled}
            onChange={(value) => setField("rag_email_enabled", value)}
            disabled={!form.rag_enabled}
          />
          <Toggle
            label="Include PDF attachments"
            checked={form.rag_pdf_enabled}
            onChange={(value) => setField("rag_pdf_enabled", value)}
            disabled={!form.rag_enabled}
          />
          <Toggle
            label="Auto-index enabled sources during scheduled Gmail polling"
            checked={form.rag_auto_index}
            onChange={(value) => setField("rag_auto_index", value)}
            disabled={!form.rag_enabled || (!form.rag_email_enabled && !form.rag_pdf_enabled)}
          />
          <label className="field">
            <span>Embedding provider</span>
            <select
              value={form.embedding_provider}
              onChange={(event) => setField("embedding_provider", event.target.value)}
              disabled={!form.rag_enabled || (!form.rag_email_enabled && !form.rag_pdf_enabled)}
            >
              <option value="local_bge_m3">Local BGE-M3</option>
              <option value="voyage">Voyage</option>
            </select>
          </label>
          <label className="field">
            <span>BGE model</span>
            <input
              value={form.bge_model}
              onChange={(event) => setField("bge_model", event.target.value)}
              disabled={!form.rag_enabled || (!form.rag_email_enabled && !form.rag_pdf_enabled) || form.embedding_provider !== "local_bge_m3"}
            />
          </label>
          <label className="field">
            <span>Voyage model</span>
            <input
              value={form.voyage_model}
              onChange={(event) => setField("voyage_model", event.target.value)}
              disabled={!form.rag_enabled || (!form.rag_email_enabled && !form.rag_pdf_enabled) || form.embedding_provider !== "voyage"}
            />
          </label>
          <label className="field">
            <span>Voyage API key {settings?.voyage_api_key_configured ? "(configured)" : "(missing)"}</span>
            <input
              type="password"
              value={form.voyage_api_key}
              placeholder="Only required when provider is Voyage"
              onChange={(event) => setField("voyage_api_key", event.target.value)}
              disabled={!form.rag_enabled || (!form.rag_email_enabled && !form.rag_pdf_enabled) || form.embedding_provider !== "voyage"}
            />
          </label>
          <label className="field">
            <span>Retrieved chunks per question</span>
            <input
              type="number"
              min="1"
              max="12"
              value={form.rag_top_k}
              onChange={(event) => setField("rag_top_k", Number(event.target.value))}
              disabled={!form.rag_enabled || (!form.rag_email_enabled && !form.rag_pdf_enabled)}
            />
          </label>
          <p className="settingsHint">
            Email body search is best for inbox questions and thread context. PDF attachment search is best for forms, policies, and documents. Refresh indexes only the sources enabled here.
          </p>
        </section>
      </div>
    </form>
  );
}

function Toggle({ label, checked, onChange, disabled = false }) {
  return (
    <label className={`toggleRow${disabled ? " disabled" : ""}`}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        disabled={disabled}
      />
      <span>{label}</span>
    </label>
  );
}

function formatDate(value) {
  if (!value) {
    return "No due date";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  const locale = typeof window !== "undefined" && new URLSearchParams(window.location.search).get("demo") === "1"
    ? "en-US"
    : undefined;
  return new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
