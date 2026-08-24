import { ipcRenderer } from "electron";
import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("friday", {
  platform: process.platform,
  hide: () => ipcRenderer.send("friday:hide"),
  show: () => ipcRenderer.send("friday:show"),
});
