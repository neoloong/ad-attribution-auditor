import { useSyncExternalStore } from "react";
import { getStore, subscribe } from "./audit-store";
export type { AuditStore, UploadedFiles } from "./audit-store";

const getServerSnapshot = () => getStore();

export function useAuditStore() {
  return useSyncExternalStore(subscribe, getStore, getServerSnapshot);
}
