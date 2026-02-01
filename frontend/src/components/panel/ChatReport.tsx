import { Download } from "lucide-react";

export interface ReportSection {
  title: string;
  content?: string;
  items?: string[];
  table?: {
    headers: string[];
    rows: string[][];
  };
}

export interface ReportSpec {
  title: string;
  subtitle?: string;
  generatedAt: string;
  sections: ReportSection[];
  exportFilename: string;
}

interface ChatReportProps {
  report: ReportSpec;
}

/**
 * Renders a structured report in the chat panel.
 * Includes header, sections with text/lists/tables, and export button.
 */
export function ChatReport({ report }: ChatReportProps) {
  const handleExport = () => {
    // Mock export - just log for now
    console.log(`[Export] Generating ${report.exportFilename}...`);
    alert(`Report "${report.exportFilename}" would be exported here.`);
  };

  return (
    <div className="my-2 rounded-lg border border-border-primary bg-bg-primary">
      {/* Report Header */}
      <div className="border-b border-border-primary px-4 py-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h4 className="text-base font-semibold text-text-primary">
              {report.title}
            </h4>
            {report.subtitle && (
              <p className="mt-0.5 text-sm text-text-muted">
                {report.subtitle}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={handleExport}
            className="flex items-center gap-1.5 rounded border border-border-primary px-2 py-1 text-xs font-medium text-text-secondary transition-colors hover:bg-bg-hover hover:text-text-primary"
          >
            <Download size={14} />
            Export
          </button>
        </div>
        <p className="mt-2 text-xs text-text-disabled">
          Generated: {report.generatedAt}
        </p>
      </div>

      {/* Report Sections */}
      <div className="divide-y divide-border-primary">
        {report.sections.map((section, i) => (
          <ReportSectionView key={i} section={section} />
        ))}
      </div>
    </div>
  );
}

function ReportSectionView({ section }: { section: ReportSection }) {
  return (
    <div className="px-4 py-3">
      <h5 className="mb-2 text-[13px] font-semibold uppercase tracking-wider text-text-muted">
        {section.title}
      </h5>

      {/* Text content */}
      {section.content && (
        <p className="text-[13px] leading-relaxed text-text-secondary">
          {section.content}
        </p>
      )}

      {/* Bullet list */}
      {section.items && (
        <ul className="space-y-1">
          {section.items.map((item, i) => (
            <li key={i} className="flex gap-2 text-[13px] text-text-secondary">
              <span className="text-text-muted">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Table */}
      {section.table && (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border-primary">
                {section.table.headers.map((header, i) => (
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
              {section.table.rows.map((row, i) => (
                <tr key={i} className="border-b border-border-primary/50">
                  {row.map((cell, j) => (
                    <td key={j} className="py-1.5 pr-3 text-text-secondary">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
