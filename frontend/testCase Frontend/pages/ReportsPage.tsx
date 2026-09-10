'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  CheckCircle2,
  ExternalLink,
  FolderKanban,
  Globe,
  Layers,
  LoaderCircle,
  PlayCircle,
  RefreshCw,
  XCircle,
  Zap,
} from 'lucide-react';
import { projectService, BackendProject } from '@/services/projectService';
import { testCaseApi } from '../services/testCaseApi';
import { loadTestProjectArtifacts, useTestCaseWorkflowStore, type GenerationSummary } from '../store/workflowStore';
import type { ExecutionReport } from '../types';

export function ReportsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlProjectId = searchParams.get('projectId');
  const urlWorkflowId = searchParams.get('workflowId');

  const { projectId: storeProjectId, setProject } = useTestCaseWorkflowStore();
  const activeProjectId = urlProjectId || storeProjectId || '';

  const [projects, setProjects] = useState<BackendProject[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(activeProjectId);
  const [selectedProject, setSelectedProject] = useState<BackendProject | null>(null);
  const [generations, setGenerations] = useState<GenerationSummary[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string>(urlWorkflowId || '');
  const [report, setReport] = useState<ExecutionReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load available projects
  useEffect(() => {
    projectService.getProjects()
      .then((items) => {
        if (Array.isArray(items)) {
          setProjects(items);
          if (!selectedProjectId && items.length > 0) {
            setSelectedProjectId(items[0].id);
          }
        }
      })
      .catch(() => undefined);
  }, [selectedProjectId]);

  // Sync selected project details & generations
  useEffect(() => {
    if (!selectedProjectId) {
      setLoading(false);
      return;
    }
    setProject(selectedProjectId);
    let disposed = false;
    setLoading(true);

    Promise.all([
      projectService.getProject(selectedProjectId).catch(() => null),
      projectService.getGenerations(selectedProjectId).catch(() => []),
    ]).then(([proj, gens]) => {
      if (disposed) return;
      if (proj) setSelectedProject(proj);
      if (Array.isArray(gens)) {
        setGenerations(gens);
        if (gens.length > 0 && (!selectedWorkflowId || !gens.some((g) => g.workflow_id === selectedWorkflowId))) {
          setSelectedWorkflowId(gens[0].workflow_id);
        }
      }
      setLoading(false);
    });

    return () => {
      disposed = true;
    };
  }, [selectedProjectId, setProject, selectedWorkflowId]);

  // Load execution report for selected generation
  useEffect(() => {
    if (!selectedWorkflowId) {
      setReport(null);
      return;
    }

    const artifacts = loadTestProjectArtifacts(selectedWorkflowId);
    if (artifacts?.report) {
      setReport(artifacts.report);
    } else {
      setReport(null);
    }

    // Attempt to fetch fresh execution job/report if executionJobId exists
    if (artifacts?.executionJobId) {
      testCaseApi.getExecutionJob(artifacts.executionJobId)
        .then((job) => {
          if (job?.report) {
            setReport(job.report);
          }
        })
        .catch(() => undefined);
    }
  }, [selectedWorkflowId]);

  const handleRefresh = async () => {
    if (!selectedWorkflowId) return;
    setRefreshing(true);
    try {
      const artifacts = loadTestProjectArtifacts(selectedWorkflowId);
      if (artifacts?.executionJobId) {
        const job = await testCaseApi.getExecutionJob(artifacts.executionJobId);
        if (job?.report) {
          setReport(job.report);
        }
      }
    } finally {
      setRefreshing(false);
    }
  };

  const targetAddress = selectedProject?.application_url || '';

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 py-6">
      {/* ── TOP BREADCRUMB & HEADER ACTIONS ────────────────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link
          href={selectedProjectId ? `/projects/${selectedProjectId}` : '/dashboard'}
          className="inline-flex items-center gap-2 text-xs font-bold text-muted-foreground hover:text-primary transition"
        >
          <ArrowLeft className="h-4 w-4" /> {selectedProjectId ? 'Back to Project Workspace' : 'Back to Dashboard'}
        </Link>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={handleRefresh}
            disabled={refreshing || !selectedWorkflowId}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-bold hover:bg-muted transition disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 text-primary ${refreshing ? 'animate-spin' : ''}`} />
            <span>Refresh Reports</span>
          </button>
          <Link
            href={selectedProjectId ? `/test-case-generation/automation?projectId=${selectedProjectId}` : '/test-case-generation/automation'}
            className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow hover:opacity-95 transition"
          >
            <Zap className="h-4 w-4" />
            <span>Execute Test Scripts</span>
          </Link>
        </div>
      </div>

      {/* ── PROJECT & GENERATION CONTEXT SELECTOR BAR ──────────────────── */}
      <section className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-primary">
                <PlayCircle className="h-3.5 w-3.5" />
                Execution Reports
              </span>
            </div>
            <h1 className="text-xl font-extrabold tracking-tight text-foreground md:text-2xl">
              Application Test Execution Evidence
            </h1>
            <p className="text-xs text-muted-foreground mt-1">
              Deterministic Playwright test execution results, pass/fail status, and verified user interface step mappings.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Project Selector */}
            <div className="space-y-1">
              <label htmlFor="report-project-select" className="block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Application Project
              </label>
              <select
                id="report-project-select"
                value={selectedProjectId}
                onChange={(e) => {
                  setSelectedProjectId(e.target.value);
                  setSelectedWorkflowId('');
                  router.push(`/test-case-generation/reports?projectId=${e.target.value}`);
                }}
                className="rounded-xl border border-border/80 bg-background px-3 py-2 text-xs font-semibold outline-none focus:border-primary transition min-w-44"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Generation Selector */}
            {generations.length > 0 && (
              <div className="space-y-1">
                <label htmlFor="report-gen-select" className="block text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                  Requirement Generation
                </label>
                <select
                  id="report-gen-select"
                  value={selectedWorkflowId}
                  onChange={(e) => setSelectedWorkflowId(e.target.value)}
                  className="rounded-xl border border-border/80 bg-background px-3 py-2 text-xs font-semibold outline-none focus:border-primary transition min-w-48"
                >
                  {generations.map((g, idx) => (
                    <option key={g.workflow_id} value={g.workflow_id}>
                      Generation {generations.length - idx} ({g.scenarios?.length ?? 0} Scenarios)
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Target Application Web Address metadata chip */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-border/60 text-xs">
          <div className="flex items-center gap-1.5 rounded-xl border border-border/70 bg-background/60 px-3 py-1.5 text-muted-foreground font-medium">
            <Globe className="h-3.5 w-3.5 text-primary" />
            <span>Target Application Web Address:</span>
            <strong className="text-foreground">{targetAddress || 'Not configured'}</strong>
            {targetAddress && (
              <a href={targetAddress} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary ml-1" title="Open Target Application Web Address">
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>

          <div className="flex items-center gap-1.5 rounded-xl border border-border/70 bg-background/60 px-3 py-1.5 font-semibold text-foreground">
            <Layers className="h-3.5 w-3.5 text-purple-500" />
            <span>{generations.length} {generations.length === 1 ? 'Requirement Generation' : 'Requirement Generations'}</span>
          </div>
        </div>
      </section>

      {/* ── LOADING SKELETON ────────────────────────────────────────────── */}
      {loading ? (
        <div className="space-y-4 animate-pulse">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-24 rounded-2xl border border-border/80 bg-card p-4" />
            ))}
          </div>
          <div className="h-64 rounded-3xl border border-border/80 bg-card p-6" />
        </div>
      ) : report ? (
        /* ── REPORT CONTENT (METRICS & SCRIPT BREAKDOWN) ─────────────────── */
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div className="rounded-2xl border border-border bg-card p-5 text-center shadow-sm">
              <span className="block text-3xl font-extrabold text-foreground">{report.total_scripts}</span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mt-1 block">Total Scripts</span>
            </div>
            <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-5 text-center shadow-sm">
              <span className="block text-3xl font-extrabold text-emerald-600 dark:text-emerald-400">{report.passed_scripts}</span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mt-1 block">Passed Scripts</span>
            </div>
            <div className="rounded-2xl border border-rose-500/30 bg-rose-500/5 p-5 text-center shadow-sm">
              <span className="block text-3xl font-extrabold text-rose-600 dark:text-rose-400">{report.failed_scripts}</span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mt-1 block">Failed Scripts</span>
            </div>
            <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-5 text-center shadow-sm">
              <span className="block text-3xl font-extrabold text-amber-600 dark:text-amber-400">{report.skipped_scripts}</span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mt-1 block">Skipped Scripts</span>
            </div>
            <div className="rounded-2xl border border-purple-500/30 bg-purple-500/5 p-5 text-center shadow-sm">
              <span className="block text-3xl font-extrabold text-purple-600 dark:text-purple-400">{report.success_percentage}%</span>
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mt-1 block">Success Rate</span>
            </div>
          </div>

          {/* Script Results Breakdown */}
          <section className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b border-border/60 pb-3">
              <div>
                <h2 className="text-base font-bold text-foreground">Executed Test Cases &amp; Automation Scripts</h2>
                <p className="text-xs text-muted-foreground">Individual script execution timing and verification status</p>
              </div>
              <span className="text-xs font-mono text-muted-foreground">
                Duration: {report.execution_time_seconds.toFixed(2)}s
              </span>
            </div>

            <div className="space-y-3">
              {report.results.map((res, idx) => (
                <div
                  key={`${res.script_id}-${idx}`}
                  className="rounded-2xl border border-border/70 bg-background/50 p-4 transition hover:bg-muted/20"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2.5">
                      {res.status === 'passed' ? (
                        <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
                      ) : res.status === 'failed' ? (
                        <XCircle className="h-5 w-5 text-rose-500 shrink-0" />
                      ) : (
                        <span className="h-2.5 w-2.5 rounded-full bg-amber-500 shrink-0" />
                      )}
                      <div>
                        <span className="text-sm font-bold text-foreground">{res.script_name || res.script_id}</span>
                        <span className="ml-2 text-xs font-mono text-muted-foreground">({res.test_case_id})</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-muted-foreground">{res.duration_seconds.toFixed(2)}s</span>
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider ${
                          res.status === 'passed'
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : res.status === 'failed'
                            ? 'bg-rose-500/10 text-rose-600 dark:text-rose-400'
                            : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {res.status}
                      </span>
                    </div>
                  </div>

                  {res.error_message && (
                    <div className="mt-3 rounded-xl border border-rose-500/20 bg-rose-500/5 p-3 text-xs font-mono text-rose-600 dark:text-rose-400">
                      {res.error_message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : (
        /* ── EMPTY STATE (PROMPT SPECIFIED) ──────────────────────────────── */
        <section className="rounded-3xl border border-border/80 bg-card p-12 text-center shadow-sm max-w-2xl mx-auto space-y-6">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-muted/60 text-muted-foreground">
            <PlayCircle className="h-8 w-8 text-primary" />
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-foreground">No Execution Reports Yet</h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Execution reports are automatically generated when Playwright test scripts are executed against the deployed application. To generate reports, crawl the application, generate requirements &amp; test cases, and execute the generated test scripts on the Automation page.
            </p>
          </div>

          <div className="flex flex-wrap justify-center gap-3 pt-2">
            <Link
              href={selectedProjectId ? `/test-case-generation/automation?projectId=${selectedProjectId}` : '/test-case-generation/automation'}
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground shadow hover:opacity-95 transition"
            >
              <Zap className="h-4 w-4" />
              <span>Go to Automation</span>
            </Link>

            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-xl border border-border bg-background px-5 py-2.5 text-xs font-bold text-foreground hover:bg-muted transition"
            >
              <FolderKanban className="h-4 w-4" />
              <span>View Application Projects</span>
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}
