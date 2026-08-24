import { app, BrowserWindow, Tray, Menu, nativeImage, ipcMain } from "electron";
import * as path from "path";
import { spawn, ChildProcess } from "child_process";
import * as fs from "fs";
import * as http from "http";

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let backendProcess: ChildProcess | null = null;

const isDev = !app.isPackaged;
const BACKEND_HEALTH = "http://127.0.0.1:8765/health";
const VITE_URL = "http://127.0.0.1:5173";

function getBackendPath(): { python: string; script: string; cwd: string } {
  const backendDir = isDev
    ? path.join(__dirname, "..", "..", "backend")
    : path.join(process.resourcesPath, "backend");
  return {
    python: process.platform === "win32" ? "python" : "python3",
    script: path.join(backendDir, "main.py"),
    cwd: backendDir,
  };
}

function checkBackend(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(BACKEND_HEALTH, (res) => {
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(800, () => {
      req.destroy();
      resolve(false);
    });
  });
}

function startBackend(): void {
  const { python, script, cwd } = getBackendPath();
  if (!fs.existsSync(script)) {
    console.warn("Backend script not found:", script);
    return;
  }
  backendProcess = spawn(python, [script], {
    cwd,
    stdio: "inherit",
    env: { ...process.env },
  });
  backendProcess.on("error", (err) => console.error("Backend error:", err));
}

async function ensureBackend(): Promise<void> {
  if (await checkBackend()) {
    console.log("Backend already running — skip spawn");
    return;
  }
  // Dev: `npm run dev` already starts uvicorn. Don't bind 8765 twice.
  if (isDev) {
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 250));
      if (await checkBackend()) return;
    }
    console.warn("Dev backend not ready on 8765 — UI will retry via websocket");
    return;
  }
  startBackend();
  for (let i = 0; i < 30; i++) {
    await new Promise((r) => setTimeout(r, 300));
    if (await checkBackend()) return;
  }
  console.warn("Backend did not become ready in time");
}

function coverPrimaryDisplay(win: BrowserWindow): void {
  win.setFullScreen(false);
  if (!win.isVisible()) win.show();
  win.maximize();
  win.moveTop();
  win.focus();
}

function waitForUrl(url: string, attempts = 40): Promise<void> {
  return new Promise((resolve, reject) => {
    let left = attempts;
    const tryOnce = () => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve();
      });
      req.on("error", () => {
        left -= 1;
        if (left <= 0) reject(new Error(`Timeout waiting for ${url}`));
        else setTimeout(tryOnce, 250);
      });
    };
    tryOnce();
  });
}

async function createWindow(): Promise<void> {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    title: "FRIDAY",
    frame: false,
    autoHideMenuBar: true,
    fullscreen: false,
    fullscreenable: true,
    transparent: false,
    backgroundColor: "#00050a",
    show: false,
    skipTaskbar: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.setMenuBarVisibility(false);

  if (isDev) {
    try {
      await waitForUrl(VITE_URL);
      await mainWindow.loadURL(VITE_URL);
    } catch (err) {
      console.error(err);
      await mainWindow.loadURL(
        `data:text/html,<body style="background:#00080c;color:#3ad6e8;font-family:monospace;padding:40px">
         <h1>FRIDAY</h1>
         <p>Vite UI is not running on ${VITE_URL}.</p>
         <p>Run: npm run dev</p></body>`
      );
    }
  } else {
    await mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.once("ready-to-show", () => {
    if (mainWindow) coverPrimaryDisplay(mainWindow);
  });
  // Vite HMR / delayed paint: enforce cover again after first frame.
  mainWindow.webContents.once("did-finish-load", () => {
    setTimeout(() => {
      if (mainWindow && !mainWindow.isDestroyed()) coverPrimaryDisplay(mainWindow);
    }, 50);
  });

  mainWindow.on("close", (e) => {
    if (tray) {
      e.preventDefault();
      mainWindow?.hide();
    }
  });
}

function createTray(): void {
  const iconPath = path.join(__dirname, "..", "public", "tray-icon.png");
  const icon = fs.existsSync(iconPath)
    ? nativeImage.createFromPath(iconPath)
    : nativeImage.createEmpty();
  tray = new Tray(
    icon.isEmpty()
      ? nativeImage.createFromDataURL(
          "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
      : icon
  );

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Show FRIDAY",
      click: () => {
        if (mainWindow) coverPrimaryDisplay(mainWindow);
      },
    },
    {
      label: "Hide",
      click: () => mainWindow?.hide(),
    },
    { type: "separator" },
    {
      label: "Quit",
      click: () => {
        tray?.destroy();
        tray = null;
        app.quit();
      },
    },
  ]);

  tray.setToolTip("FRIDAY AI Assistant");
  tray.setContextMenu(contextMenu);
  tray.on("double-click", () => {
    if (mainWindow) coverPrimaryDisplay(mainWindow);
  });
}

function applyAutostart(): void {
  let autostart = true;
  try {
    const cfgPath = path.join(process.env.APPDATA || "", "FRIDAY", "config.json");
    if (fs.existsSync(cfgPath)) {
      const cfg = JSON.parse(fs.readFileSync(cfgPath, "utf8"));
      autostart = cfg.autostart !== false;
    }
  } catch {
    autostart = true;
  }

  try {
    app.setLoginItemSettings({ openAtLogin: autostart });
  } catch (err) {
    console.warn("login item failed", err);
  }

  const script = path.join(__dirname, "..", "..", "..", "scripts", "install-autostart.ps1");
  if (fs.existsSync(script)) {
    const args = ["-ExecutionPolicy", "Bypass", "-File", script];
    if (!autostart) args.push("-Remove");
    spawn("powershell.exe", args, { windowsHide: true, detached: true, stdio: "ignore" }).unref();
  }
}

app.setName("FRIDAY");
app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
if (process.platform === "win32") {
  app.setAppUserModelId("com.friday.assistant");
}

app.whenReady().then(async () => {
  Menu.setApplicationMenu(null);
  applyAutostart();
  ipcMain.on("friday:hide", () => {
    mainWindow?.minimize();
  });
  ipcMain.on("friday:show", () => {
    if (mainWindow) coverPrimaryDisplay(mainWindow);
  });
  await ensureBackend();
  await createWindow();
  createTray();
});

app.on("window-all-closed", () => {
  // keep running in tray on Windows
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

process.on("exit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
