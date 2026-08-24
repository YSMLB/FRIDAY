export {};

declare global {
  interface Window {
    friday?: {
      platform: string;
      hide?: () => void;
      show?: () => void;
    };
  }
}
