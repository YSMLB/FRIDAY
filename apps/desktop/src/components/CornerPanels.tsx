export type CornerSlot = "tl" | "tr" | "bl" | "br";

export interface CornerInfo {
  id: string;
  slot: CornerSlot;
  title: string;
  body: string;
  meta?: string;
}

interface CornerPanelsProps {
  items: CornerInfo[];
  onDismiss: (id: string) => void;
}

export function CornerPanels({ items, onDismiss }: CornerPanelsProps) {
  return (
    <div className="corner-panels">
      {items.map((item) => (
        <aside
          key={item.id}
          className={`corner-panel ${item.slot} visible`}
          role="status"
        >
          <div className="corner-panel-title">
            <span>{item.title}</span>
            <button type="button" onClick={() => onDismiss(item.id)} aria-label="Dismiss">
              ×
            </button>
          </div>
          <div className="corner-panel-body">{item.body}</div>
          {item.meta ? <div className="corner-panel-meta">{item.meta}</div> : null}
        </aside>
      ))}
    </div>
  );
}
