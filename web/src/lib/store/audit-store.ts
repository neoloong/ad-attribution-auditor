import type { AuditResult } from "@/lib/engine";
import type { AdDaily, GSCDaily, ShopifyDaily } from "@/lib/ingestion/types";

export interface UploadedFiles {
  metaAds: AdDaily[] | null;
  googleAds: AdDaily[] | null;
  shopifyOrders: ShopifyDaily[] | null;
  gscBrandSearch: GSCDaily[] | null;
}

export interface AuditStore {
  uploadedFiles: UploadedFiles;
  auditResult: AuditResult | null;
  isRunning: boolean;
  error: string | null;
}

let store: AuditStore = {
  uploadedFiles: {
    metaAds: null,
    googleAds: null,
    shopifyOrders: null,
    gscBrandSearch: null,
  },
  auditResult: null,
  isRunning: false,
  error: null,
};

type Listener = () => void;
const listeners = new Set<Listener>();

export function getStore(): AuditStore {
  return store;
}

export function setStore(partial: Partial<AuditStore>) {
  store = { ...store, ...partial };
  listeners.forEach((l) => l());
}

export function subscribe(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function resetStore() {
  store = {
    uploadedFiles: {
      metaAds: null,
      googleAds: null,
      shopifyOrders: null,
      gscBrandSearch: null,
    },
    auditResult: null,
    isRunning: false,
    error: null,
  };
  listeners.forEach((l) => l());
}
