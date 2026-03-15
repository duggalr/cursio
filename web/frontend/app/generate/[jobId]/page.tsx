"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchJobStatus, type Job } from "@/lib/api";

const steps = [
  { key: "planning", label: "Planning", description: "Outlining the lesson structure" },
  { key: "generating", label: "Generating", description: "Writing animation code" },
  { key: "rendering", label: "Rendering", description: "Creating visual animations" },
  { key: "voiceover", label: "Voiceover", description: "Generating narration audio" },
  { key: "assembling", label: "Assembling", description: "Combining video and audio" },
  { key: "complete", label: "Complete", description: "Your video is ready" },
];

function getStepIndex(status: string): number {
  const idx = steps.findIndex((s) => s.key === status);
  return idx === -1 ? 0 : idx;
}

export default function JobProgressPage() {
  const params = useParams();
  const jobId = params.jobId as string;

  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    try {
      const data = await fetchJobStatus(jobId);
      setJob(data);

      if (data.status === "complete" || data.status === "failed") {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
    }
  }, [jobId]);

  useEffect(() => {
    poll();
    intervalRef.current = setInterval(poll, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [poll]);

  const currentStepIdx = job ? getStepIndex(job.status) : -1;

  return (
    <div className="mx-auto max-w-lg px-6 py-16">
      <div className="mb-10 text-center">
        <h1
          className="mb-2 text-2xl text-[var(--color-foreground)]"
          style={{ fontFamily: "var(--font-serif)" }}
        >
          {job?.status === "complete"
            ? "Video Ready"
            : job?.status === "failed"
              ? "Generation Failed"
              : "Creating Your Video"}
        </h1>
        <p className="text-sm text-[var(--color-muted)]">
          {job?.status === "complete"
            ? "Your educational video has been generated."
            : job?.status === "failed"
              ? "Something went wrong during generation."
              : "This usually takes a few minutes."}
        </p>
      </div>

      {error && !job && (
        <div className="rounded-lg bg-red-50 p-4 text-center">
          <p className="mb-3 text-sm text-red-700">{error}</p>
          <Link href="/" className="text-sm text-[var(--color-foreground)] underline">
            Back to home
          </Link>
        </div>
      )}

      {/* Step Progress */}
      <div className="mb-10 rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6">
        <div className="space-y-0">
          {steps.map((step, idx) => {
            const isComplete = currentStepIdx > idx;
            const isCurrent = currentStepIdx === idx && job?.status !== "failed";
            const isFailed = job?.status === "failed" && currentStepIdx === idx;
            const isPending = currentStepIdx < idx;

            return (
              <div key={step.key} className="flex items-start gap-3">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition-all ${
                      isComplete
                        ? "border-green-500 bg-green-50"
                        : isCurrent
                          ? "border-[var(--color-foreground)] bg-[var(--color-surface-hover)]"
                          : isFailed
                            ? "border-red-500 bg-red-50"
                            : "border-[var(--color-border)] bg-[var(--color-background)]"
                    }`}
                  >
                    {isComplete ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-600" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    ) : isCurrent ? (
                      <div className="h-2 w-2 animate-pulse rounded-full bg-[var(--color-foreground)]" />
                    ) : isFailed ? (
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-red-500" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    ) : (
                      <span className="text-[10px] text-[var(--color-muted)]">{idx + 1}</span>
                    )}
                  </div>
                  {idx < steps.length - 1 && (
                    <div
                      className={`h-6 w-px ${
                        isComplete ? "bg-green-300" : "bg-[var(--color-border)]"
                      }`}
                    />
                  )}
                </div>

                <div className="pb-6 pt-1">
                  <h3
                    className={`text-sm ${
                      isComplete
                        ? "text-green-700"
                        : isCurrent
                          ? "font-medium text-[var(--color-foreground)]"
                          : isFailed
                            ? "text-red-600"
                            : "text-[var(--color-muted)]"
                    }`}
                  >
                    {step.label}
                  </h3>
                  <p className={`text-xs ${isPending ? "text-[var(--color-border)]" : "text-[var(--color-muted)]"}`}>
                    {step.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {job?.status === "complete" && job.video_id && (
        <div className="text-center">
          <Link
            href={`/video/${job.video_id}`}
            className="inline-block rounded-lg bg-[var(--color-foreground)] px-6 py-2.5 text-sm font-medium text-[var(--color-background)] transition-opacity hover:opacity-90"
          >
            Watch Now
          </Link>
        </div>
      )}

      {job?.status === "failed" && (
        <div className="text-center">
          {job.error && (
            <p className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
              {job.error}
            </p>
          )}
          <Link href="/" className="text-sm text-[var(--color-foreground)] underline">
            Back to home
          </Link>
        </div>
      )}
    </div>
  );
}
