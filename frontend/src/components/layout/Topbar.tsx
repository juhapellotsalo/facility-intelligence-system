import { CanvasTabs, type CanvasView } from "./CanvasTabs";

interface TopbarProps {
  activeView: CanvasView;
  onViewChange: (view: CanvasView) => void;
}

export function Topbar({ activeView, onViewChange }: TopbarProps) {
  return (
    <header className="col-span-2 flex items-center gap-4 border-b border-bg-border bg-bg-surface px-4">
      <h1 className="text-sm font-semibold tracking-wide text-text-primary">
        FACILITY INTELLIGENCE SYSTEM
      </h1>
      <div className="h-5 w-px bg-bg-border" />
      <CanvasTabs activeView={activeView} onViewChange={onViewChange} />
    </header>
  );
}
