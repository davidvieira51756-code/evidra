"use client";

import { ChangeEvent, FormEvent, useMemo, useState } from "react";

type Finding = {
  id: string;
  title: string;
  cryptoAssetName: string;
  status: "QUANTUM_VULNERABLE" | "POST_QUANTUM" | "REVIEW_REQUIRED" | string;
  reason: string;
  algorithm: string | null;
  componentName: string | null;
  componentVersion: string | null;
  recommendation: string;
  evidence: string[];
};

type AnalysisSummary = {
  bomFormat: string;
  specVersion: string;
  componentCount: number;
  cryptoAssetCount: number;
  findingCount: number;
  quantumVulnerableFindingCount: number;
  postQuantumFindingCount: number;
  reviewRequiredFindingCount: number;
};

type AnalysisResponse = {
  status: string;
  summary: AnalysisSummary;
  findings: Finding[];
  nextActions: string[];
};

type FindingExplanation = {
  findingId: string;
  summary: string;
  riskExplanation: string;
  migrationConsiderations: string[];
  suggestedTests: string[];
  limitations: string[];
};

type ApiError = {
  code?: string;
  message?: string;
  error?: string;
  detail?: unknown;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_CORE_API_URL ?? "http://localhost:8080";

const statusLabels: Record<string, string> = {
  QUANTUM_VULNERABLE: "Quantum vulnerable",
  POST_QUANTUM: "Post-quantum",
  REVIEW_REQUIRED: "Review required",
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const canSubmit = useMemo(() => file !== null && !isAnalyzing, [file, isAnalyzing]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setAnalysis(null);
    setError(null);
  }

  async function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Select a CBOM file first.");
      return;
    }

    setIsAnalyzing(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/api/cboms/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const apiError = (await response.json().catch(() => ({}))) as ApiError;
        throw new Error(apiError.message ?? "CBOM analysis failed.");
      }

      setAnalysis((await response.json()) as AnalysisResponse);
    } catch (caughtError) {
      setAnalysis(null);
      setError(caughtError instanceof Error ? caughtError.message : "CBOM analysis failed.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleExportReport() {
    if (!file) {
      setError("Select a CBOM file first.");
      return;
    }

    setIsExporting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE_URL}/api/cboms/report`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const apiError = (await response.json().catch(() => ({}))) as ApiError;
        throw new Error(apiError.message ?? "Report export failed.");
      }

      const report = await response.text();
      const blob = new Blob([report], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "evidra-cbom-report.md";
      link.click();
      URL.revokeObjectURL(url);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Report export failed.");
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#171717]">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-6 py-8">
        <header className="flex flex-col gap-3 border-b border-[#d8d8d2] pb-6">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[#596157]">
              Evidra
            </p>
            <h1 className="mt-2 text-3xl font-semibold">
              CBOM cryptographic analysis
            </h1>
          </div>
          <p className="max-w-3xl text-sm leading-6 text-[#52544f]">
            Import a CycloneDX CBOM, identify cryptographic assets, generate deterministic findings,
            and export a reviewable migration report.
          </p>
        </header>

        <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
          <form
            onSubmit={handleAnalyze}
            className="flex flex-col gap-5 rounded border border-[#d8d8d2] bg-white p-5"
          >
            <div>
              <h2 className="text-base font-semibold">Import CBOM</h2>
              <p className="mt-1 text-sm leading-6 text-[#666963]">
                Use a CycloneDX JSON file. The MVP analyzes deterministic CBOM signals only.
              </p>
            </div>

            <label className="flex cursor-pointer flex-col gap-3 rounded border border-dashed border-[#bfc2bb] bg-[#fbfbf8] p-4">
              <span className="text-sm font-medium">CBOM file</span>
              <input
                className="text-sm file:mr-3 file:rounded file:border-0 file:bg-[#24382f] file:px-3 file:py-2 file:text-sm file:font-medium file:text-white"
                type="file"
                accept="application/json,.json"
                onChange={handleFileChange}
              />
              <span className="min-h-5 text-sm text-[#666963]">
                {file ? file.name : "No file selected"}
              </span>
            </label>

            {error ? (
              <div className="rounded border border-[#d9a4a0] bg-[#fff2f1] p-3 text-sm text-[#8b2c25]">
                {error}
              </div>
            ) : null}

            <div className="flex flex-wrap gap-3">
              <button
                className="rounded bg-[#24382f] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-[#a9aea8]"
                type="submit"
                disabled={!canSubmit}
              >
                {isAnalyzing ? "Analyzing..." : "Analyze CBOM"}
              </button>
              <button
                className="rounded border border-[#bfc2bb] px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-[#9a9d98]"
                type="button"
                onClick={handleExportReport}
                disabled={!file || isExporting}
              >
                {isExporting ? "Exporting..." : "Export report"}
              </button>
            </div>
          </form>

          <div className="flex flex-col gap-6">
            {analysis ? <AnalysisView analysis={analysis} /> : <EmptyState />}
          </div>
        </section>
      </div>
    </main>
  );
}

function AnalysisView({ analysis }: { analysis: AnalysisResponse }) {
  return (
    <>
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Metric label="Components" value={analysis.summary.componentCount} />
        <Metric label="Crypto assets" value={analysis.summary.cryptoAssetCount} />
        <Metric label="Findings" value={analysis.summary.findingCount} />
        <Metric
          label="Quantum vulnerable"
          value={analysis.summary.quantumVulnerableFindingCount}
        />
      </section>

      <section className="rounded border border-[#d8d8d2] bg-white p-5">
        <h2 className="text-base font-semibold">Findings</h2>
        <div className="mt-4 flex flex-col gap-3">
          {analysis.findings.length === 0 ? (
            <p className="text-sm text-[#666963]">No cryptographic findings were generated.</p>
          ) : (
            analysis.findings.map((finding) => <FindingCard key={finding.id} finding={finding} />)
          )}
        </div>
      </section>

      <section className="rounded border border-[#d8d8d2] bg-white p-5">
        <h2 className="text-base font-semibold">Next actions</h2>
        <ul className="mt-4 flex flex-col gap-2">
          {analysis.nextActions.map((action) => (
            <li className="rounded bg-[#f4f4ef] px-3 py-2 text-sm leading-6" key={action}>
              {action}
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded border border-[#d8d8d2] bg-white p-4">
      <p className="text-sm text-[#666963]">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </div>
  );
}

function FindingCard({ finding }: { finding: Finding }) {
  const [explanation, setExplanation] = useState<FindingExplanation | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [explanationError, setExplanationError] = useState<string | null>(null);

  async function handleExplainFinding() {
    setIsExplaining(true);
    setExplanationError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/findings/explain`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ finding }),
      });

      if (!response.ok) {
        const apiError = (await response.json().catch(() => ({}))) as ApiError;
        throw new Error(formatApiError(apiError, "Finding explanation failed."));
      }

      setExplanation((await response.json()) as FindingExplanation);
    } catch (caughtError) {
      setExplanation(null);
      setExplanationError(
        caughtError instanceof Error ? caughtError.message : "Finding explanation failed.",
      );
    } finally {
      setIsExplaining(false);
    }
  }

  return (
    <article className="rounded border border-[#d8d8d2] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold">{finding.title}</h3>
          <p className="mt-1 text-sm text-[#666963]">
            {finding.componentName ?? "unknown component"}
            {finding.componentVersion ? ` ${finding.componentVersion}` : ""}
          </p>
        </div>
        <span className={statusClassName(finding.status)}>
          {statusLabels[finding.status] ?? finding.status}
        </span>
      </div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium text-[#4f5851]">Algorithm</dt>
          <dd className="mt-1">{finding.algorithm ?? "unknown"}</dd>
        </div>
        <div>
          <dt className="font-medium text-[#4f5851]">Crypto asset</dt>
          <dd className="mt-1">{finding.cryptoAssetName}</dd>
        </div>
      </dl>
      <p className="mt-4 text-sm leading-6 text-[#4a4d49]">{finding.reason}</p>
      <p className="mt-2 text-sm leading-6 text-[#4a4d49]">{finding.recommendation}</p>

      <div className="mt-4">
        <button
          className="rounded border border-[#bfc2bb] px-3 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:text-[#9a9d98]"
          type="button"
          onClick={handleExplainFinding}
          disabled={isExplaining}
        >
          {isExplaining ? "Explaining..." : "Explain finding"}
        </button>
      </div>

      {explanationError ? (
        <div className="mt-4 rounded border border-[#d9a4a0] bg-[#fff2f1] p-3 text-sm text-[#8b2c25]">
          {explanationError}
        </div>
      ) : null}

      {explanation ? <FindingExplanationPanel explanation={explanation} /> : null}
    </article>
  );
}

function FindingExplanationPanel({ explanation }: { explanation: FindingExplanation }) {
  return (
    <section className="mt-4 rounded border border-[#d8d8d2] bg-[#fbfbf8] p-4">
      <h4 className="text-sm font-semibold">Structured explanation</h4>
      <p className="mt-2 text-sm leading-6 text-[#4a4d49]">{explanation.summary}</p>
      <p className="mt-2 text-sm leading-6 text-[#4a4d49]">{explanation.riskExplanation}</p>

      <ExplanationList title="Migration considerations" items={explanation.migrationConsiderations} />
      <ExplanationList title="Suggested tests" items={explanation.suggestedTests} />
      <ExplanationList title="Limitations" items={explanation.limitations} />
    </section>
  );
}

function ExplanationList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="mt-4">
      <h5 className="text-sm font-medium text-[#4f5851]">{title}</h5>
      <ul className="mt-2 flex flex-col gap-2">
        {items.map((item) => (
          <li className="rounded bg-white px-3 py-2 text-sm leading-6" key={item}>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

function EmptyState() {
  return (
    <section className="flex min-h-[420px] items-center justify-center rounded border border-[#d8d8d2] bg-white p-8 text-center">
      <div className="max-w-md">
        <h2 className="text-lg font-semibold">No analysis yet</h2>
        <p className="mt-2 text-sm leading-6 text-[#666963]">
          Upload a CBOM to see summary metrics, deterministic findings, and recommended next actions.
        </p>
      </div>
    </section>
  );
}

function formatApiError(apiError: ApiError, fallback: string) {
  if (apiError.message) {
    return apiError.message;
  }

  if (apiError.error) {
    return apiError.error;
  }

  if (apiError.detail) {
    return typeof apiError.detail === "string"
      ? apiError.detail
      : JSON.stringify(apiError.detail);
  }

  return fallback;
}

function statusClassName(status: string) {
  const base = "rounded px-2 py-1 text-xs font-semibold";
  if (status === "QUANTUM_VULNERABLE") {
    return `${base} bg-[#ffe9dc] text-[#8a3b12]`;
  }
  if (status === "POST_QUANTUM") {
    return `${base} bg-[#e5f4ea] text-[#245f38]`;
  }
  return `${base} bg-[#eef0f2] text-[#45515b]`;
}
