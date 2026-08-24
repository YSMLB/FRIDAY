import { useState } from "react";
import { FridayConfig, LLMProvider } from "@shared/protocol";

interface SettingsPanelProps {
  config: FridayConfig;
  onSave: (config: Partial<FridayConfig>) => void;
  onClose: () => void;
  onVoiceToggle: (enabled: boolean) => void;
}

const PROVIDER_MODELS: Record<LLMProvider, string> = {
  ollama: "qwen2.5:3b",
  qwen: "qwen3.7-flash",
  openai: "gpt-4o",
  anthropic: "claude-3-5-sonnet-latest",
  google: "gemini-2.0-flash",
};

const PROVIDER_BASE: Partial<Record<LLMProvider, string>> = {
  ollama: "http://127.0.0.1:11434/v1",
  qwen: "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
};

function fromConfig(config: FridayConfig) {
  return {
    llmProvider: config.llmProvider,
    llmModel: config.llmModel,
    llmBaseUrl: config.llmBaseUrl || "",
    wakeWordEnabled: config.wakeWordEnabled,
    wakeWord: config.wakeWord,
    ttsVoice: config.ttsVoice,
    sttModel: config.sttModel,
    autostart: config.autostart,
    splashDurationMs: config.splashDurationMs,
  };
}

export function SettingsPanel({ config, onSave, onClose, onVoiceToggle }: SettingsPanelProps) {
  const [local, setLocal] = useState(fromConfig(config));

  const setProvider = (llmProvider: LLMProvider) => {
    setLocal({
      ...local,
      llmProvider,
      llmModel: PROVIDER_MODELS[llmProvider],
      llmBaseUrl: PROVIDER_BASE[llmProvider] || "",
    });
  };

  const handleSave = () => {
    onSave(local);
    onVoiceToggle(local.wakeWordEnabled);
    onClose();
  };

  return (
    <div className="settings-overlay">
      <div className="settings-panel">
        <div className="settings-header">
          <h2>CONFIGURATION</h2>
          <button type="button" className="btn-close" onClick={onClose}>
            ×
          </button>
        </div>

        <p className="settings-hint">
          Рекомендуется <strong>Ollama</strong> — локально, без оплаты токенов.
          {config.llmProvider === "ollama"
            ? " Сейчас: Ollama."
            : config.hasQwenKey
              ? " Qwen key: loaded."
              : ""}
        </p>

        <label>
          LLM Provider
          <select
            value={local.llmProvider}
            onChange={(e) => setProvider(e.target.value as LLMProvider)}
          >
            <option value="ollama">Ollama (local, free)</option>
            <option value="qwen">Qwen (QwenCloud)</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="google">Google Gemini</option>
          </select>
        </label>

        <label>
          Model
          <input
            value={local.llmModel}
            onChange={(e) => setLocal({ ...local, llmModel: e.target.value })}
            placeholder={PROVIDER_MODELS[local.llmProvider]}
          />
        </label>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={local.wakeWordEnabled}
            onChange={(e) => setLocal({ ...local, wakeWordEnabled: e.target.checked })}
          />
          Wake word enabled
        </label>

        <label>
          Wake word
          <input
            value={local.wakeWord}
            onChange={(e) => setLocal({ ...local, wakeWord: e.target.value })}
          />
        </label>

        <label>
          TTS Voice
          <input
            value={local.ttsVoice}
            onChange={(e) => setLocal({ ...local, ttsVoice: e.target.value })}
          />
        </label>

        <label>
          STT Model (Whisper)
          <select
            value={local.sttModel}
            onChange={(e) => setLocal({ ...local, sttModel: e.target.value })}
          >
            <option value="tiny">tiny</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium</option>
          </select>
        </label>

        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={local.autostart}
            onChange={(e) => setLocal({ ...local, autostart: e.target.checked })}
          />
          Autostart on boot
        </label>

        <div className="settings-actions">
          <button type="button" className="btn-primary" onClick={handleSave}>
            SAVE
          </button>
          <button type="button" className="btn-secondary" onClick={onClose}>
            CANCEL
          </button>
        </div>
      </div>
    </div>
  );
}
