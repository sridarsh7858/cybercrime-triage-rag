import { useRef, useState } from "react";
import Navbar from "../components/Navbar";
import { analyzeIncident } from "../api/client";

const SAMPLE =
  "Victim received a call from someone posing as a bank official asking to complete KYC. They shared an OTP and ₹48,000 was debited via UPI to an unknown account.";

export default function Dashboard() {
  const [query, setQuery] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const inputRef = useRef(null);

  const acceptFile = (f) => {
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setError("Please attach an image file (screenshot).");
      return;
    }
    setError("");
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const clearFile = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    acceptFile(e.dataTransfer.files?.[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!query.trim() && !file) {
      setError("Provide a complaint description or attach a screenshot (or both).");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      const data = await analyzeIncident({ query, file });
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="cyber-bg min-h-screen">
      <Navbar />

      <main className="mx-auto max-w-6xl px-5 py-8">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-white">File an Incident</h2>
          <p className="mt-1 text-sm text-slate-400">
            Describe the cybercrime and/or attach a screenshot. The engine runs OCR,
            retrieves similar historical cases, and returns a structured triage.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* ---- Input form ---- */}
          <form onSubmit={handleSubmit} className="glass rounded-2xl p-5 sm:p-6">
            <div className="mb-2 flex items-center justify-between">
              <label className="text-xs font-medium uppercase tracking-wider text-slate-400">
                Complaint narrative
              </label>
              <button
                type="button"
                onClick={() => setQuery(SAMPLE)}
                className="text-xs text-cyan-400 hover:text-cyan-300"
              >
                Insert sample
              </button>
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={7}
              placeholder="Describe what happened — who contacted the victim, what was requested, amounts, platforms involved…"
              className="glow-ring mb-5 w-full resize-y rounded-lg border border-white/10 bg-ink-900/60 px-3.5 py-3 text-sm leading-relaxed text-white placeholder:text-slate-500"
            />

            <label className="mb-2 block text-xs font-medium uppercase tracking-wider text-slate-400">
              Evidence screenshot
            </label>

            {!preview ? (
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                onClick={() => inputRef.current?.click()}
                className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition ${
                  dragging
                    ? "border-cyan-400/70 bg-cyan-400/5"
                    : "border-white/15 hover:border-cyan-400/40 hover:bg-white/[0.03]"
                }`}
              >
                <svg
                  className="mb-2 h-8 w-8 text-slate-400"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <path d="M17 8l-5-5-5 5" />
                  <path d="M12 3v12" />
                </svg>
                <p className="text-sm text-slate-300">
                  <span className="text-cyan-400">Click to upload</span> or drag & drop
                </p>
                <p className="mt-1 text-xs text-slate-500">PNG, JPG or WEBP</p>
              </div>
            ) : (
              <div className="relative overflow-hidden rounded-xl border border-white/10">
                <img
                  src={preview}
                  alt="Evidence preview"
                  className="max-h-64 w-full object-contain bg-black/40"
                />
                <div className="flex items-center justify-between gap-3 border-t border-white/10 bg-ink-900/70 px-3 py-2">
                  <span className="truncate text-xs text-slate-300">{file?.name}</span>
                  <button
                    type="button"
                    onClick={clearFile}
                    className="shrink-0 rounded-md border border-white/10 px-2 py-1 text-xs text-slate-300 hover:border-rose-400/40 hover:text-rose-200"
                  >
                    Remove
                  </button>
                </div>
              </div>
            )}
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => acceptFile(e.target.files?.[0])}
            />

            {error && (
              <div className="mt-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3.5 py-2.5 text-sm text-rose-200">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="glow-ring mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-2.5 text-sm font-semibold text-ink-950 shadow-[0_0_24px_rgba(34,211,238,0.3)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Spinner /> Analyzing…
                </>
              ) : (
                <>Run Triage Analysis</>
              )}
            </button>
          </form>

          {/* ---- Result panel ---- */}
          <section className="glass flex min-h-[22rem] flex-col rounded-2xl p-5 sm:p-6">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-300">
                Triage Report
              </h3>
              {result && (
                <span className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-300">
                  {result.retrieved_context_count} similar case
                  {result.retrieved_context_count === 1 ? "" : "s"} matched
                </span>
              )}
            </div>

            <div className="thin-scroll flex-1 overflow-y-auto">
              {loading && <LoadingState />}
              {!loading && !result && !error && <EmptyState />}
              {!loading && result && <AnalysisView text={result.analysis} />}
              {!loading && !result && error && (
                <div className="mt-6 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  {error}
                </div>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

function Spinner() {
  return (
    <span className="spin inline-block h-4 w-4 rounded-full border-2 border-ink-950/40 border-t-ink-950" />
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center py-10 text-center">
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-slate-400">
        <svg
          className="h-6 w-6"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <path d="M14 2v6h6" />
          <path d="M16 13H8M16 17H8M10 9H8" />
        </svg>
      </div>
      <p className="text-sm text-slate-400">
        Your structured triage report will appear here.
      </p>
      <p className="mt-1 text-xs text-slate-500">
        Threat classification · legal category · mitigation steps
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-3 py-2">
      <div className="flex items-center gap-2 text-sm text-cyan-300">
        <Spinner /> Retrieving cases and consulting the model…
      </div>
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="h-3 animate-pulse rounded bg-white/5"
          style={{ width: `${90 - i * 8}%` }}
        />
      ))}
    </div>
  );
}

/**
 * Renders the LLM's plain-text analysis. Numbered headings (e.g. "1. Threat
 * Classification") are emphasised; everything else flows as readable paragraphs.
 */
function AnalysisView({ text }) {
  const lines = (text || "").split(/\r?\n/);
  return (
    <div className="space-y-2.5 text-sm leading-relaxed text-slate-200">
      {lines.map((raw, i) => {
        const line = raw.trim();
        if (!line) return <div key={i} className="h-1" />;
        const isHeading = /^(\d+[.)]|#{1,3})\s+/.test(line) || /^\*\*.+\*\*:?$/.test(line);
        const clean = line.replace(/\*\*/g, "");
        if (isHeading) {
          return (
            <h4
              key={i}
              className="pt-1 text-[13px] font-semibold uppercase tracking-wide text-cyan-300"
            >
              {clean}
            </h4>
          );
        }
        const isBullet = /^[-*•]\s+/.test(line);
        return (
          <p key={i} className={isBullet ? "pl-4 text-slate-300" : "text-slate-300"}>
            {isBullet ? "• " + clean.replace(/^[-*•]\s+/, "") : clean}
          </p>
        );
      })}
    </div>
  );
}
