export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? ""; // same origin; next.config.ts proxies /api to the backend

export type Job = {
  id: string;
  title: string;
  company: string;
  tags: string[];
  url: string;
  description: string;
  source?: string;
  category?: string;
};

// Earned vs fabricated: how much of an LLM rewrite's ATS gain the original
// resume actually supports (backend/research/audit.py).
export type ClaimType = "skill" | "metric" | "role_scope" | "credential" | "content";

export type AuditUnit = {
  text: string;
  claims: { type: ClaimType; text: string; reason: string }[];
  closest_original: string;
};

export type AuditResponse = {
  source: "generated" | "pasted";
  refusal: boolean;
  model: string | null;
  scores: { orig: number; llm: number; stripped: number; guarded?: number };
  gain: number;
  earned_gain: number;
  fabricated_gain: number;
  fabricated_share: number | null;
  min_gain: number;
  counts: Record<ClaimType, number>;
  n_units: number;
  n_flagged_units: number;
  guarded_rounds: number;
  lines: AuditUnit[][];
  texts: { orig: string; llm: string; stripped: string; guarded?: string };
};

export class BackendUnreachableError extends Error {
  constructor() {
    super("Can't reach the backend. Start it with: cd backend && .venv\\Scripts\\uvicorn app.main:app --port 8420");
    this.name = "BackendUnreachableError";
  }
}

export class BackendHttpError extends Error {
  status: number;
  constructor(status: number, body?: string) {
    super(`Backend returned ${status}${body ? `: ${body}` : ""}`);
    this.name = "BackendHttpError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BACKEND_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") throw err;
    throw new BackendUnreachableError();
  }
  if (!res.ok) {
    let body: string | undefined;
    try {
      body = await res.text();
    } catch {
      // ignore
    }
    throw new BackendHttpError(res.status, body);
  }
  return (await res.json()) as T;
}

export const fetchJobs = () => request<{ jobs: Job[] }>("/api/jobs");

// demo/cases.json: an original, a job and a typical AI rewrite, ready to audit without a model
export type DemoCase = {
  id: string;
  shows: string;
  job: { title: string; company?: string; description: string };
  original: string;
  rewrite: string;
};

export const fetchDemoCases = () => request<{ cases: DemoCase[] }>("/api/demo/cases");

export const fetchAuditExample =() => request<{ resume_text: string; job: Job }>("/api/audit/example");

export const postAudit = (
  resume_text: string,
  job: Job,
  rewrite_text: string,
  guarded: boolean,
  signal?: AbortSignal,
) =>
  request<AuditResponse>("/api/audit", {
    method: "POST",
    body: JSON.stringify({ resume_text, job, rewrite_text, guarded }),
    signal,
  });
