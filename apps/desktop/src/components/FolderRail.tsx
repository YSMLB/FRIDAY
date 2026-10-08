import { useEffect, useState } from "react";
import { BACKEND_HTTP_URL } from "@shared/protocol";

export interface LibraryItem {
  id: string;
  name: string;
  kind: string;
  launch: string;
}

export interface LibraryFolder {
  id: string;
  label: string;
  items: LibraryItem[];
}

interface FolderRailProps {
  onLaunch: (target: string) => void;
}

export function FolderRail({ onLaunch }: FolderRailProps) {
  const [folders, setFolders] = useState<LibraryFolder[]>([]);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const res = await fetch(`${BACKEND_HTTP_URL}/system/library`);
        if (!res.ok || stop) return;
        const data = await res.json();
        setFolders(data.folders || []);
      } catch {
        /* backend warming up */
      }
    };
    load();
    const id = window.setInterval(load, 30000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, []);

  const active = folders.find((f) => f.id === openId) || null;

  return (
    <aside className="folder-rail">
      <div className="folder-list">
        {folders.map((folder) => (
          <button
            key={folder.id}
            type="button"
            className={`folder-btn ${openId === folder.id ? "active" : ""}`}
            onClick={() => setOpenId((v) => (v === folder.id ? null : folder.id))}
          >
            <span className="folder-ico" />
            <span>{folder.label}</span>
            <em>{folder.items.length}</em>
          </button>
        ))}
      </div>

      {active ? (
        <div className="folder-panel">
          <div className="folder-panel-head">
            <strong>{active.label}</strong>
            <button type="button" onClick={() => setOpenId(null)}>
              ×
            </button>
          </div>
          <div className="folder-items">
            {active.items.length === 0 ? (
              <p className="folder-empty">Nothing found yet</p>
            ) : (
              active.items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="folder-item"
                  onClick={() => onLaunch(item.launch)}
                  title={item.launch}
                >
                  <span>{item.name}</span>
                  <i>{item.kind}</i>
                </button>
              ))
            )}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
