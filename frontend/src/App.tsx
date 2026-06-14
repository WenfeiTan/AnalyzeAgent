import { useEffect, useRef, useState } from "react";

import { ApiClientError, api, watchJob } from "./api/client";
import type {
  ApiConfiguration,
  InitialJobRequest,
  JobResponse,
  RequirementSummary,
  StageEvent,
  UpdateJobRequest,
} from "./api/types";
import { HistoryPanel } from "./components/HistoryPanel";
import { InitialForm } from "./components/InitialForm";
import { JobProgress } from "./components/JobProgress";
import { ResultView } from "./components/ResultView";
import { UpdateForm } from "./components/UpdateForm";

type View = "initial" | "update" | "history";

export function App() {
  const [view, setView] = useState<View>("initial");
  const [configuration, setConfiguration] =
    useState<ApiConfiguration | null>(null);
  const [requirements, setRequirements] = useState<RequirementSummary[]>([]);
  const [job, setJob] = useState<JobResponse | null>(null);
  const [events, setEvents] = useState<StageEvent[]>([]);
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const stopWatching = useRef<(() => void) | null>(null);

  const refreshRequirements = async () => {
    try {
      setRequirements(await api.requirements());
    } catch {
      setRequirements([]);
    }
  };

  useEffect(() => {
    void api.configuration().then(setConfiguration).catch(() => {
      setError("Backend is unavailable. Start it on port 8000.");
    });
    void refreshRequirements();
    return () => stopWatching.current?.();
  }, []);

  const startJob = async (
    submission: Promise<{ job_id: string }>,
  ) => {
    setError("");
    setEvents([]);
    setJob(null);
    setRunning(true);
    stopWatching.current?.();
    try {
      const created = await submission;
      stopWatching.current = watchJob(created.job_id, {
        onStage: (event) =>
          setEvents((items) => [
            ...items.filter(
              (item) =>
                !(
                  item.sequence === event.sequence &&
                  item.status === event.status
                ),
            ),
            event,
          ]),
        onJob: (completed) => {
          setJob(completed);
          setRunning(false);
          if (completed.status === "completed") {
            void refreshRequirements();
          }
        },
        onError: (eventError) => {
          setError(eventError.message);
          setRunning(false);
        },
      });
    } catch (submissionError) {
      setRunning(false);
      setError(
        submissionError instanceof ApiClientError
          ? submissionError.message
          : "Unable to submit the workflow.",
      );
    }
  };

  const scenarios = configuration?.scenarios ?? ["empty"];

  return (
    <div className="app">
      <header className="topbar">
        <a className="brand" href="/">
          <span className="brand-mark">A</span>
          <div>
            <strong>Analyze Agent</strong>
            <small>Asset Discovery workspace</small>
          </div>
        </a>
        <div className="environment">
          <span className="fake-badge">Fake Knowledge Base</span>
          <span
            className={`connection ${
              configuration?.api_key_configured ? "ready" : "blocked"
            }`}
          >
            <i />
            {configuration
              ? configuration.api_key_configured
                ? `${configuration.model} ready`
                : "Gemini API key missing"
              : "Connecting to Backend"}
          </span>
        </div>
      </header>

      <nav className="workspace-nav" aria-label="Workflow navigation">
        {(["initial", "update", "history"] as View[]).map((item) => (
          <button
            className={view === item ? "active" : ""}
            key={item}
            type="button"
            onClick={() => setView(item)}
          >
            {item === "initial"
              ? "Initial analysis"
              : item === "update"
                ? "Update requirement"
                : "History"}
          </button>
        ))}
      </nav>

      <main className="workspace">
        <section className="workspace-intro">
          <div>
            <p className="kicker">Development & product demo</p>
            <h1>Turn requirements into search-ready guidance.</h1>
          </div>
          <p>
            Inspect clear fields, semantic keywords, reusable mappings and every
            real workflow stage before handing output to Elastic Search.
          </p>
        </section>

        {error && <div className="global-error">{error}</div>}

        {view === "history" ? (
          <HistoryPanel requirements={requirements} />
        ) : (
          <div className="workflow-layout">
            <div>
              {view === "initial" ? (
                <InitialForm
                  scenarios={scenarios}
                  running={running}
                  unavailable={configuration?.api_key_configured === false}
                  onSubmit={(payload: InitialJobRequest) =>
                    startJob(api.submitInitial(payload))
                  }
                />
              ) : (
                <UpdateForm
                  requirements={requirements}
                  scenarios={scenarios}
                  running={running}
                  unavailable={configuration?.api_key_configured === false}
                  onSubmit={(payload: UpdateJobRequest) =>
                    startJob(api.submitUpdate(payload))
                  }
                />
              )}
            </div>
            <JobProgress job={job} events={events} />
          </div>
        )}
        <ResultView job={job} />
      </main>
    </div>
  );
}
