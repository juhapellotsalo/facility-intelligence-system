import { Download } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "../../data/mockResponses";
import { ChatChart } from "./ChatChart";
import { ChatReport } from "./ChatReport";

interface ChatMessageProps {
  message: ChatMessageType;
  onAction?: (query: string) => void;
}

/**
 * Renders a single chat message with markdown-like formatting.
 * User messages align right, assistant messages align left.
 * Includes inline chart/report rendering when data is present.
 * Supports action anchors: [[Display Text|query]] syntax for clickable actions.
 */
export function ChatMessage({ message, onAction }: ChatMessageProps) {
  const isUser = message.role === "user";
  const hasContent = message.content || message.chart || message.report;

  // Don't render empty assistant messages (placeholder during streaming)
  if (!isUser && !hasContent) {
    return null;
  }

  const handleExport = () => {
    // TODO: Implement PDF export
    console.log(
      "[Export] PDF export - content:",
      message.content?.slice(0, 100),
    );
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg px-3 py-2 ${
          isUser
            ? "bg-accent-blue/15 text-text-primary"
            : "bg-bg-raised text-text-secondary"
        }`}
      >
        {message.content && (
          <div className="text-[13px] leading-relaxed">
            <FormattedContent content={message.content} onAction={onAction} />
          </div>
        )}
        {message.chart && <ChatChart chart={message.chart} />}
        {message.report && <ChatReport report={message.report} />}
        {message.isReport && (
          <div className="mt-3 flex justify-end border-t border-text-muted/20 pt-3">
            <button
              type="button"
              onClick={handleExport}
              className="flex items-center gap-1.5 rounded border border-cyan-400/30 px-2 py-1 text-xs text-cyan-400 transition-colors hover:bg-cyan-400/10"
            >
              <Download size={12} />
              Export PDF
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface FormattedProps {
  onAction?: (query: string) => void;
}

/**
 * Enhanced markdown-like formatting for message content.
 * Supports: **bold**, bullet points, numbered lists, tables, horizontal rules,
 * section headers, [[action|query]] anchors
 */
function FormattedContent({
  content,
  onAction,
}: { content: string } & FormattedProps) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Check for table (line with | characters, followed by separator line)
    if (line.includes("|") && lines[i + 1]?.match(/^\|?[\s-|]+\|?$/)) {
      const tableLines: string[] = [line];
      i++;
      // Collect all table lines
      while (
        i < lines.length &&
        (lines[i].includes("|") || lines[i].match(/^\|?[\s-|]+\|?$/))
      ) {
        tableLines.push(lines[i]);
        i++;
      }
      elements.push(<FormattedTable key={`table-${i}`} lines={tableLines} />);
      continue;
    }

    elements.push(
      <FormattedLine
        key={i}
        line={line}
        isLast={i === lines.length - 1}
        onAction={onAction}
      />,
    );
    i++;
  }

  return <>{elements}</>;
}

/**
 * Renders a markdown-style table
 */
function FormattedTable({ lines }: { lines: string[] }) {
  // Parse header row
  const headerLine = lines[0];
  const headers = headerLine
    .split("|")
    .map((h) => h.trim())
    .filter(Boolean);

  // Skip separator line, parse data rows
  const dataRows = lines
    .slice(2)
    .filter((line) => line.includes("|") && !line.match(/^[\s-|]+$/));
  const rows = dataRows.map((line) =>
    line
      .split("|")
      .map((cell) => cell.trim())
      .filter(Boolean),
  );

  return (
    <div className="my-2 overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="border-b border-text-muted/20">
            {headers.map((header, i) => (
              <th
                key={i}
                className="py-1.5 pr-3 text-left font-semibold text-text-muted"
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-text-muted/10">
              {row.map((cell, j) => (
                <td key={j} className="py-1.5 pr-3 text-text-secondary">
                  <InlineFormatted text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FormattedLine({
  line,
  isLast,
  onAction,
}: { line: string; isLast: boolean } & FormattedProps) {
  const trimmed = line.trim();

  // Empty line = paragraph break
  if (trimmed === "") {
    return <div className="h-2" />;
  }

  // Horizontal rule (--- or ___)
  if (/^[-_]{3,}$/.test(trimmed)) {
    return <hr className="my-2 border-text-muted/20" />;
  }

  // Markdown ## header (report title)
  const h2Match = trimmed.match(/^##\s+(.+)$/);
  if (h2Match) {
    return (
      <div className="mt-3 mb-2 text-base font-bold text-cyan-400 first:mt-0">
        {h2Match[1]}
      </div>
    );
  }

  // Markdown ### header (section header)
  const h3Match = trimmed.match(/^###\s+(.+)$/);
  if (h3Match) {
    return (
      <div className="mt-3 mb-1 text-[13px] font-semibold uppercase tracking-wide text-cyan-400/80">
        {h3Match[1]}
      </div>
    );
  }

  // ALL CAPS section header (like "INCIDENT SUMMARY", "DETAILS", etc.)
  if (/^[A-Z][A-Z\s]{2,}$/.test(trimmed) && trimmed.length < 40) {
    return (
      <div className="mt-3 mb-1 text-[11px] font-bold uppercase tracking-wider text-cyan-400/80">
        {trimmed}
      </div>
    );
  }

  // Header line (starts and ends with **) - use trimmed to handle whitespace
  if (
    trimmed.startsWith("**") &&
    trimmed.endsWith("**") &&
    !trimmed.slice(2, -2).includes("**")
  ) {
    return (
      <div className="mt-2 mb-1 font-semibold text-text-primary first:mt-0">
        {trimmed.slice(2, -2)}
      </div>
    );
  }

  // Numbered list item (1. 2. 3. etc.)
  const numberedMatch = line.match(/^(\d+)\.\s+(.+)$/);
  if (numberedMatch) {
    return (
      <div className="ml-1 flex gap-2">
        <span className="w-4 text-right text-cyan-400/60">
          {numberedMatch[1]}.
        </span>
        <span className="flex-1">
          <InlineFormatted text={numberedMatch[2]} onAction={onAction} />
        </span>
      </div>
    );
  }

  // Bullet point (- or •)
  if (line.startsWith("- ") || line.startsWith("• ")) {
    return (
      <div className="ml-1 flex gap-2">
        <span className="text-cyan-400/60">•</span>
        <span className="flex-1">
          <InlineFormatted text={line.slice(2)} onAction={onAction} />
        </span>
      </div>
    );
  }

  // Warning/info callout (emoji at start)
  if (/^[⚠️🔴🟡🟢🚨⛔✓✅❌]/.test(trimmed)) {
    return (
      <div className="my-1 rounded border-l-2 border-status-warning bg-status-warning-bg/30 py-1 pl-2 pr-1">
        <InlineFormatted text={line} onAction={onAction} />
      </div>
    );
  }

  // Status line (like "Status: OPEN")
  if (/^Status:\s/i.test(trimmed)) {
    return (
      <div className="mt-2 rounded bg-cyan-400/10 px-2 py-1 text-cyan-400">
        <InlineFormatted text={line} onAction={onAction} />
      </div>
    );
  }

  // Regular line
  return (
    <div className={isLast ? "" : "mb-0.5"}>
      <InlineFormatted text={line} onAction={onAction} />
    </div>
  );
}

/**
 * Inline formatting: **bold** text and [[action|query]] anchors
 * Action syntax: [[Display Text|query to send]] or [[query]] (uses query as display)
 */
function InlineFormatted({
  text,
  onAction,
}: { text: string } & FormattedProps) {
  // Combined regex for **bold** and [[action|query]] patterns
  // Use non-greedy match for bold to handle multiple bold sections
  const parts = text.split(/(\*\*.*?\*\*|\[\[[^\]]+\]\])/g);

  return (
    <>
      {parts.map((part, i) => {
        // Bold text
        if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
          return (
            <strong key={i} className="font-semibold text-text-primary">
              {part.slice(2, -2)}
            </strong>
          );
        }

        // Action anchor: [[Display|query]] or [[query]]
        if (part.startsWith("[[") && part.endsWith("]]")) {
          const inner = part.slice(2, -2);
          const pipeIndex = inner.indexOf("|");
          const display = pipeIndex >= 0 ? inner.slice(0, pipeIndex) : inner;
          const query = pipeIndex >= 0 ? inner.slice(pipeIndex + 1) : inner;

          return (
            <button
              key={i}
              type="button"
              onClick={() => onAction?.(query)}
              className="inline text-cyan-400 underline decoration-cyan-400/40 underline-offset-2 transition-colors hover:text-cyan-300 hover:decoration-cyan-300/60"
            >
              {display}
            </button>
          );
        }

        return <span key={i}>{part}</span>;
      })}
    </>
  );
}

/**
 * Typing indicator shown while "AI is thinking"
 */
export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-lg bg-bg-raised px-3 py-2">
        <div className="h-2 w-2 animate-bounce rounded-full bg-cyan-400/60 [animation-delay:-0.3s]" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-cyan-400/60 [animation-delay:-0.15s]" />
        <div className="h-2 w-2 animate-bounce rounded-full bg-cyan-400/60" />
      </div>
    </div>
  );
}

/**
 * Thinking indicator showing current reasoning step.
 * Displays in a subtle style and shows only the most recent step.
 */
export function ThinkingIndicator({ text }: { text: string }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 px-3 py-2">
        <svg
          className="h-4 w-4 animate-spin text-cyan-400/50"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
        <span className="text-xs text-text-secondary italic">{text}</span>
      </div>
    </div>
  );
}
