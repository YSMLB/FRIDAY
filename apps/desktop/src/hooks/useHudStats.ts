import { useEffect, useState } from "react";
import { BACKEND_HTTP_URL } from "@shared/protocol";

export interface HudSnapshot {
  hardware: {
    cpu: string;
    gpu: string;
    ram: string;
    disk: string;
    board: string;
  };
  cpuPercent: number;
  ramPercent: number;
  ramUsed: string;
  downloadKBs: number;
  uploadKBs: number;
  battery: { percent: number; plugged: boolean } | null;
  browsers: string[];
}

const EMPTY: HudSnapshot = {
  hardware: { cpu: "CPU", gpu: "GPU", ram: "RAM", disk: "DISK", board: "MOBO" },
  cpuPercent: 0,
  ramPercent: 0,
  ramUsed: "",
  downloadKBs: 0,
  uploadKBs: 0,
  battery: null,
  browsers: ["edge", "chrome", "firefox"],
};

export function useHudStats() {
  const [hud, setHud] = useState<HudSnapshot>(EMPTY);

  useEffect(() => {
    let stop = false;
    const tick = async () => {
      try {
        const res = await fetch(`${BACKEND_HTTP_URL}/system/hud`);
        if (!res.ok || stop) return;
        setHud(await res.json());
      } catch {
        /* backend not ready */
      }
    };
    tick();
    const id = window.setInterval(tick, 2000);
    return () => {
      stop = true;
      window.clearInterval(id);
    };
  }, []);

  return hud;
}
