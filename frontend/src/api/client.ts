import type {
  ApiConfiguration,
  InitialJobRequest,
  JobResponse,
  JobSubmission,
  RequirementSummary,
  Revision,
  StageEvent,
  UpdateJobRequest,
} from "./types";

const API_BASE_URL = (
  import.meta.env.VITE_ANALYZE_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiClientError extends Error {
  constructor(
    message: string,
    readonly code = "api_error",
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new ApiClientError(
      payload?.error?.message ?? "The Analyze Agent API request failed.",
      payload?.error?.code,
    );
  }
  return payload as T;
}

export const api = {
  configuration: () =>
    request<ApiConfiguration>("/api/v1/configuration"),
  requirements: () =>
    request<RequirementSummary[]>("/api/v1/requirements"),
  revisions: (requirementId: string) =>
    request<Revision[]>(
      `/api/v1/requirements/${encodeURIComponent(requirementId)}/revisions`,
    ),
  submitInitial: (payload: InitialJobRequest) =>
    request<JobSubmission>("/api/v1/jobs/initial", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  submitUpdate: (payload: UpdateJobRequest) =>
    request<JobSubmission>("/api/v1/jobs/update", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  job: (jobId: string) =>
    request<JobResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}`),
};

export function watchJob(
  jobId: string,
  handlers: {
    onStage: (event: StageEvent) => void;
    onJob: (job: JobResponse) => void;
    onError: (error: Error) => void;
  },
): () => void {
  const source = new EventSource(
    `${API_BASE_URL}/api/v1/jobs/${encodeURIComponent(jobId)}/events`,
  );
  source.addEventListener("stage", (message) => {
    handlers.onStage(JSON.parse((message as MessageEvent).data) as StageEvent);
  });
  source.addEventListener("job", (message) => {
    handlers.onJob(JSON.parse((message as MessageEvent).data) as JobResponse);
    source.close();
  });
  source.onerror = async () => {
    source.close();
    try {
      handlers.onJob(await api.job(jobId));
    } catch (error) {
      handlers.onError(
        error instanceof Error ? error : new Error("Event stream failed."),
      );
    }
  };
  return () => source.close();
}
