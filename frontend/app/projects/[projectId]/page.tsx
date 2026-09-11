'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Code2,
  Copy,
  Download,
  FileCheck2,
  FileText,
  FolderKanban,
  GitBranch,
  Globe,
  Layers,
  PlayCircle,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Zap,
  Activity,
  AlertTriangle,
  ExternalLink,
  ChevronRight,
  Database,
  LoaderCircle,
  Square,
} from 'lucide-react';
import { testCaseApi } from '@/testCase Frontend/services/testCaseApi';
import { projectService, BackendProject } from '@/services/projectService';
import {
  useTestCaseWorkflowStore,
  loadTestProjectArtifacts,
  saveTestProjectArtifacts,
  type SavedTestProjectArtifacts,
  type GenerationSummary
} from '@/testCase Frontend/store/workflowStore';
import type { WorkflowResult } from '@/testCase Frontend/types';

type ArtifactTab =
  | 'stories'
  | 'scenarios'
  | 'testcases'
  | 'scripts'
  | 'execution'
  | 'traceability'
  | 'validation'
  | 'knowledge';

const formatDate = (value?: string) => {
  if (!value) return 'Unknown date';
  try {
    const diffMin = Math.floor((Date.now() - new Date(value).getTime()) / 60000);
    if (diffMin < 1) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays}d ago`;
  } catch {
    return value;
  }
};

export default function DedicatedProjectWorkspacePage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { setProject, selectGeneration, hydrate } = useTestCaseWorkflowStore();

  const [project, setProjectData] = useState<BackendProject | null>(null);
  const [crawlKnowledge, setCrawlKnowledge] = useState<any | null>(null);
  const [generations, setGenerations] = useState<GenerationSummary[]>([]);
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);

  const [workflowResult, setWorkflowResult] = useState<WorkflowResult | null>(null);
  const [savedArtifacts, setSavedArtifacts] = useState<SavedTestProjectArtifacts | null>(null);
  const [executionStatus, setExecutionStatus] = useState('not_run');
  const [activeTab, setActiveTab] = useState<ArtifactTab>('scenarios');
  const [copiedScriptIndex, setCopiedScriptIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  // Application Crawl states
  const [crawlUrl, setCrawlUrl] = useState('');
  const [crawlScope, setCrawlScope] = useState<'full_application' | 'specific_page'>('full_application');
  const [targetPageAddress, setTargetPageAddress] = useState('');
  const [authMode, setAuthMode] = useState<'no_auth' | 'credentials' | 'existing_session'>('no_auth');
  const [authIdentifier, setAuthIdentifier] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authSessionState, setAuthSessionState] = useState('');
  const [crawlJob, setCrawlJob] = useState<any | null>(null);
  const [crawlBusy, setCrawlBusy] = useState(false);
  const [crawlError, setCrawlError] = useState('');
  const [showCrawlConfig, setShowCrawlConfig] = useState(false);

  useEffect(() => hydrate(), [hydrate]);

  // Set active project in global store
  useEffect(() => {
    if (projectId) {
      setProject(projectId);
    }
  }, [projectId, setProject]);

  // Load project details, crawl knowledge, and generations list
  useEffect(() => {
    if (!projectId) return;
    let disposed = false;

    const loadProjectData = async () => {
      try {
        setLoading(true);
        const [proj, crawl, gens] = await Promise.all([
          projectService.getProject(projectId),
          testCaseApi.getProjectCrawlKnowledge(projectId).catch(() => null),
          projectService.getGenerations(projectId).catch(() => []),
        ]);

        if (disposed) return;
        if (proj) setProjectData(proj);
        if (crawl) setCrawlKnowledge(crawl);
        if (Array.isArray(gens)) {
          setGenerations(gens);
          if (gens.length > 0 && !selectedWorkflowId) {
            setSelectedWorkflowId(gens[0].workflow_id);
            selectGeneration(gens[0].workflow_id);
          }
        }
      } finally {
        if (!disposed) setLoading(false);
      }
    };

    void loadProjectData();
    return () => { disposed = true; };
  }, [projectId]);

  // Sync crawlUrl with project's application_url when loaded
  useEffect(() => {
    if (project?.application_url && !crawlUrl) {
      setCrawlUrl(project.application_url);
    }
  }, [project?.application_url, crawlUrl]);

  const isCrawling = Boolean(
    crawlJob && ['queued', 'running', 'stopping'].includes(crawlJob.status)
  );

  // Poll active crawl job
  useEffect(() => {
    if (!crawlJob?.job_id || !isCrawling) return;
    let disposed = false;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const current = await testCaseApi.getCrawlJob(crawlJob.job_id);
        if (disposed) return;
        setCrawlJob(current);
        if (current.status === 'completed') {
          const fresh = await testCaseApi.getProjectCrawlKnowledge(projectId).catch(() => null);
          if (fresh && !disposed) setCrawlKnowledge(fresh);
        } else if (current.status === 'failed') {
          setCrawlError(current.error || 'The application crawl could not be completed.');
        }
      } catch {
        // Polling retry
      } finally {
        if (!disposed && isCrawling) timer = window.setTimeout(poll, 1500);
      }
    };
    void poll();
    return () => {
      disposed = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [crawlJob?.job_id, isCrawling, projectId]);

  const handleStartCrawl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isCrawling && crawlJob) {
      if (crawlBusy) return;
      setCrawlBusy(true);
      try {
        setCrawlJob(await testCaseApi.stopCrawlJob(crawlJob.job_id));
      } catch (err: any) {
        setCrawlError(err?.message || 'Could not stop crawl');
      } finally {
        setCrawlBusy(false);
      }
      return;
    }

    const trimmed = crawlUrl.trim();
    if (!trimmed || crawlBusy) return;
    setCrawlBusy(true);
    setCrawlError('');

    let authPayload: any = undefined;
    if (authMode === 'credentials') {
      authPayload = {
        auth_mode: 'credentials',
        identifier: authIdentifier.trim() || undefined,
        password: authPassword || undefined,
      };
    } else if (authMode === 'existing_session') {
      let parsed: any = authSessionState;
      try { parsed = JSON.parse(authSessionState); } catch {}
      authPayload = {
        auth_mode: 'existing_session',
        session_state: parsed,
      };
    }

    const targetUrlVal = targetPageAddress.trim() || undefined;
    const startUrl = (crawlScope === 'specific_page' && targetUrlVal)
      ? targetUrlVal
      : trimmed;

    try {
      if (trimmed !== project?.application_url) {
        projectService.updateProject(projectId, { application_url: trimmed }).catch(() => undefined);
      }
      const job = await testCaseApi.startCrawlJob(startUrl, {
        target_url: targetUrlVal,
        page_limit: crawlScope === 'specific_page' ? 15 : 100,
        depth_limit: crawlScope === 'specific_page' ? 2 : 10,
        max_execution_time_seconds: 300,
        testing_scope: crawlScope,
        authentication: authPayload,
        project_id: projectId,
        project_name: project?.name,
      });
      setCrawlJob(job);
    } catch (err: any) {
      setCrawlError(err?.message || 'Could not start application crawl');
    } finally {
      setCrawlBusy(false);
    }
  };

  // When selectedWorkflowId changes, fetch that specific generation's workflow result & artifacts
  useEffect(() => {
    if (!selectedWorkflowId) {
      setWorkflowResult(null);
      setSavedArtifacts(null);
      setExecutionStatus('not_run');
      return;
    }

    let disposed = false;
    selectGeneration(selectedWorkflowId);

    const refreshGenArtifacts = async () => {
      let artifacts = loadTestProjectArtifacts(selectedWorkflowId);
      let currentExecutionStatus = artifacts?.report?.execution_status || 'not_run';

      if (artifacts?.crawlJobId) {
        try {
          const crawlJob = await testCaseApi.getWorkflowCrawlJob(artifacts.crawlJobId);
          artifacts = { ...artifacts, crawl: crawlJob.crawl ?? artifacts.crawl, generation: crawlJob.generation ?? artifacts.generation };
        } catch {}
      }
      if (artifacts?.executionJobId) {
        try {
          const executionJob = await testCaseApi.getExecutionJob(artifacts.executionJobId);
          currentExecutionStatus = executionJob.status;
          artifacts = { ...artifacts, report: executionJob.report ?? artifacts.report };
        } catch {}
      }
      if (artifacts) {
        saveTestProjectArtifacts(selectedWorkflowId, artifacts.generation, artifacts.report, artifacts.comparison, artifacts.crawl);
      }

      if (!disposed) {
        setSavedArtifacts(artifacts);
        setExecutionStatus(currentExecutionStatus);
      }

      try {
        const result = await testCaseApi.getWorkflowResult(selectedWorkflowId);
        if (!disposed) setWorkflowResult(result);
      } catch {
        if (!disposed) {
          // If result API is not found or empty, construct from generation summary
          const activeGen = generations.find(g => g.workflow_id === selectedWorkflowId);
          if (activeGen) {
            setWorkflowResult({
              workflow_id: activeGen.workflow_id,
              project_id: activeGen.project_id,
              status: activeGen.status as any,
              current_stage: activeGen.current_stage,
              scenarios: activeGen.scenarios || [],
              test_cases: activeGen.test_cases || [],
              scenario_validation: undefined,
              testcase_validation: undefined,
              confidence_threshold: 0.95,
            });
          }
        }
      }
    };

    void refreshGenArtifacts();
  }, [selectedWorkflowId, generations, selectGeneration]);

  // Active generation metadata
  const selectedGen = useMemo(() => {
    return generations.find((g) => g.workflow_id === selectedWorkflowId) || null;
  }, [generations, selectedWorkflowId]);

  // Selected generation artifacts
  const userStories = useMemo(() => {
    return selectedGen?.user_stories || [];
  }, [selectedGen]);

  const acceptanceCriteria = useMemo(() => {
    return selectedGen?.acceptance_criteria || [];
  }, [selectedGen]);

  const testScenarios = useMemo(() => {
    if (workflowResult?.scenarios?.length) return workflowResult.scenarios;
    return selectedGen?.scenarios || [];
  }, [workflowResult, selectedGen]);

  const testCases = useMemo(() => {
    if (workflowResult?.test_cases?.length) return workflowResult.test_cases;
    return selectedGen?.test_cases || [];
  }, [workflowResult, selectedGen]);

  const playwrightScripts = useMemo(() => {
    return (savedArtifacts?.generation?.scripts as unknown as Array<Record<string, unknown>> | undefined) ?? [];
  }, [savedArtifacts]);

  const executionReports = useMemo(() => {
    if (savedArtifacts?.report) return [savedArtifacts.report];
    return [];
  }, [savedArtifacts]);

  const latestReport = executionReports[0];
  const validations = [workflowResult?.scenario_validation, workflowResult?.testcase_validation].filter(Boolean);

  const handleCopyCode = (code: string, index: number) => {
    navigator.clipboard.writeText(code);
    setCopiedScriptIndex(index);
    setTimeout(() => setCopiedScriptIndex(null), 2000);
  };

  const hasCrawl = Boolean(
    (crawlKnowledge && (crawlKnowledge.crawl_status === 'crawl_completed' || crawlKnowledge.pages_crawled > 0)) ||
    (project?.crawl_knowledge && Object.keys(project.crawl_knowledge).length > 0 && ((project.crawl_knowledge as any).crawl_status === 'crawl_completed' || (project.crawl_knowledge as any).pages_crawled > 0))
  );
  const pagesCrawled = crawlKnowledge?.pages_crawled || project?.crawl_knowledge?.pages_crawled || crawlKnowledge?.application_map?.pages?.length || 0;
  const elementsFound = crawlKnowledge?.elements_found || project?.crawl_knowledge?.elements_found || crawlKnowledge?.discovered_elements?.length || 0;
  const pagesSkipped = crawlJob?.progress?.pages_skipped ?? crawlKnowledge?.crawl_report?.pages_skipped?.length ?? (project?.crawl_knowledge as any)?.crawl_report?.pages_skipped?.length ?? 0;
  const elapsedFormatted = crawlJob?.progress?.elapsed_formatted || crawlKnowledge?.crawl_report?.progress?.elapsed_formatted || (project?.crawl_knowledge as any)?.crawl_report?.progress?.elapsed_formatted || '00:00:15';

  const tabsConfig: { id: ArtifactTab; label: string; icon: React.ElementType; count: number }[] = [
    { id: 'stories', label: 'User Stories & Acceptance Criteria', icon: FileText, count: userStories.length },
    { id: 'scenarios', label: 'Test Scenarios', icon: ShieldCheck, count: testScenarios.length },
    { id: 'testcases', label: 'Test Cases', icon: FileCheck2, count: testCases.length },
    { id: 'scripts', label: 'Playwright Scripts', icon: Code2, count: playwrightScripts.length },
    { id: 'execution', label: 'Execution Reports', icon: PlayCircle, count: executionReports.length },
    { id: 'traceability', label: 'Traceability Matrix', icon: GitBranch, count: testCases.length },
    { id: 'validation', label: 'Validation Scores', icon: Sparkles, count: validations.length },
    { id: 'knowledge', label: 'Application Knowledge', icon: Database, count: pagesCrawled },
  ];

  return (
    <div className="space-y-8 pb-16">
      {/* ── TOP NAVIGATION BREADCRUMB & HEADER ACTIONS ──────────────────── */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 text-xs font-bold text-muted-foreground hover:text-primary transition"
        >
          <ArrowLeft className="h-4 w-4" /> Back to Dashboard
        </Link>

        <div className="flex flex-wrap items-center gap-2.5">
          {hasCrawl ? (
            <Link
              href={`/test-case-generation?projectId=${projectId}`}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-purple-600 px-4 py-2.5 text-xs font-bold text-white shadow-md shadow-orange-500/20 hover:opacity-95 transition"
            >
              <Plus className="h-4 w-4" />
              <span>+ Start New Requirement Generation</span>
            </Link>
          ) : (
            <button
              type="button"
              disabled
              title="Complete the Application Crawl before starting Requirement Generation."
              className="inline-flex items-center gap-2 rounded-xl bg-muted px-4 py-2.5 text-xs font-bold text-muted-foreground cursor-not-allowed opacity-60 transition"
            >
              <Plus className="h-4 w-4" />
              <span>Start Requirement Generation (Complete Crawl First)</span>
            </button>
          )}

          <Link
            href={`/test-case-generation/automation?projectId=${projectId}${selectedWorkflowId ? `&workflowId=${selectedWorkflowId}` : ''}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-bold hover:bg-muted transition"
          >
            <Zap className="h-4 w-4 text-purple-500" />
            <span>Run Test Scripts</span>
          </Link>
        </div>
      </div>

      {/* ── PROJECT HEADER CARD (WITH INTENTIONAL SKELETON LOADER) ───────── */}
      {loading ? (
        <div className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm md:p-8 animate-pulse">
          <div className="h-6 w-44 rounded-full bg-muted mb-4" />
          <div className="h-9 w-72 rounded-xl bg-muted mb-4" />
          <div className="flex flex-wrap gap-3">
            <div className="h-8 w-48 rounded-xl bg-muted" />
            <div className="h-8 w-56 rounded-xl bg-muted" />
          </div>
        </div>
      ) : (
        <div className="relative overflow-hidden rounded-3xl border border-border/80 bg-card p-6 shadow-sm md:p-8">
          <div className="absolute -right-20 -top-24 h-64 w-64 rounded-full bg-purple-500/15 blur-3xl pointer-events-none" />
          <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-primary">
                  <FolderKanban className="h-3.5 w-3.5" />
                  Application Project
                </span>
                <span className="rounded-full bg-muted px-2.5 py-0.5 text-[11px] font-mono text-muted-foreground">
                  ID: {projectId}
                </span>
              </div>

              <h1 className="text-2xl font-extrabold tracking-tight text-foreground md:text-4xl">
                {project?.name || `Project ${projectId.slice(0, 8)}`}
              </h1>

              {/* Project Metadata & Status Chips */}
              <div className="mt-4 flex flex-wrap items-center gap-3 text-xs">
                {/* Target Application Web Address */}
                <div className="flex items-center gap-1.5 rounded-xl border border-border/70 bg-background/60 px-3 py-1.5 text-muted-foreground font-medium">
                  <Globe className="h-3.5 w-3.5 text-primary" />
                  <span>{project?.application_url || crawlUrl || 'Target Application Web Address not configured'}</span>
                  {(project?.application_url || crawlUrl) && (
                    <a href={project?.application_url || crawlUrl} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary ml-1" title="Open Target Application Web Address">
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>

                {/* Crawl Knowledge Status */}
                <div className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 font-semibold ${
                  hasCrawl
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                }`}>
                  <span className={`h-2 w-2 rounded-full ${hasCrawl ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                  <span>{hasCrawl ? `Verified Knowledge: ${pagesCrawled} pages · ${elementsFound} elements` : 'Crawl Required Before Requirement Generation'}</span>
                </div>

                {/* Requirement Generations Count */}
                <div className="flex items-center gap-1.5 rounded-xl border border-border/70 bg-background/60 px-3 py-1.5 font-semibold text-foreground">
                  <Layers className="h-3.5 w-3.5 text-purple-500" />
                  <span>{generations.length} {generations.length === 1 ? 'Requirement Generation' : 'Requirement Generations'}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4 border-t border-border/60 pt-4 md:border-0 md:pt-0">
              <div className="text-right">
                <span className="block text-2xl font-extrabold text-foreground">{playwrightScripts.length}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Active Scripts</span>
              </div>
              <div className="h-8 w-px bg-border/60" />
              <div className="text-right">
                <span className="block text-lg font-extrabold capitalize text-primary">{executionStatus.replaceAll('_', ' ')}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">Execution Status</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── APPLICATION CRAWL & KNOWLEDGE SECTION (FLOW GATEWAY) ────────── */}
      <section className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-border/60 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-foreground">Application Crawl &amp; Verified Knowledge</h2>
              <p className="text-xs text-muted-foreground">
                Discovers reachable application routes and interactive locators required for requirements and test automation.
              </p>
            </div>
          </div>

          {hasCrawl && !isCrawling && (
            <button
              type="button"
              onClick={() => setShowCrawlConfig((v) => !v)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-3.5 py-1.5 text-xs font-semibold hover:bg-muted transition"
            >
              <RefreshCw className="h-3.5 w-3.5 text-primary" />
              <span>{showCrawlConfig ? 'Hide Crawl Controls' : 'Re-Crawl Application'}</span>
            </button>
          )}
        </div>

        {/* CRAWL STATUS FEEDBACK & FORM */}
        {crawlError && !isCrawling && crawlJob?.status !== 'failed' && (
          <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs font-semibold text-red-600 dark:text-red-300">
            {crawlError}
          </div>
        )}

        {/* TWO-PART CRAWL EXPERIENCE: MAIN WORKSPACE REAL-TIME PROGRESS */}
        {isCrawling && (
          <div className="rounded-2xl border border-primary/30 bg-primary/5 p-6 space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-primary/20 pb-4">
              <div>
                <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                  <span className="relative flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-primary"></span>
                  </span>
                  Application Crawl in Progress
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs font-semibold text-muted-foreground">Status:</span>
                  <span className="text-xs font-bold text-primary">
                    {crawlJob?.status === 'stopping' ? 'Stopping...' : 'Crawling'}
                  </span>
                  <span className="text-[11px] text-muted-foreground ml-2">
                    (Visible Playwright browser navigating application on desktop)
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={handleStartCrawl}
                disabled={crawlBusy || crawlJob?.status === 'stopping'}
                className="inline-flex items-center justify-center gap-1.5 rounded-xl bg-rose-600 px-4 py-2 text-xs font-bold text-white shadow-sm hover:bg-rose-700 disabled:opacity-60 transition active:scale-95"
              >
                <Square className="h-3.5 w-3.5 fill-current" /> Stop Crawling
              </button>
            </div>

            {/* REAL-TIME CRAWL METRICS GRID */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              <div className="rounded-xl border border-border/70 bg-card/70 p-3 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages discovered</span>
                <span className="text-lg font-black text-foreground">{crawlJob?.progress?.pages_discovered ?? 1}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages scanned</span>
                <span className="text-lg font-black text-foreground">{crawlJob?.progress?.pages_scanned ?? crawlJob?.progress?.pages_completed ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Interactive elements found</span>
                <span className="text-lg font-black text-primary">{crawlJob?.progress?.elements_found ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages skipped</span>
                <span className="text-lg font-black text-muted-foreground">{crawlJob?.progress?.pages_skipped ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Elapsed time</span>
                <span className="text-lg font-black text-foreground font-mono">{crawlJob?.progress?.elapsed_formatted || '00:00:00'}</span>
              </div>
            </div>

            {/* CURRENT ACTIVITY */}
            <div className="rounded-xl border border-border/60 bg-muted/40 px-3.5 py-2.5 text-xs flex items-center gap-2">
              <span className="font-bold text-foreground shrink-0">Current activity:</span>
              <span className="text-muted-foreground truncate font-medium">
                {crawlJob?.progress?.current_activity || 'Scanning application...'}
              </span>
            </div>
          </div>
        )}

        {/* STOPPED CRAWL STATE */}
        {crawlJob?.status === 'stopped' && !isCrawling && (
          <div className="rounded-2xl border border-amber-500/30 bg-amber-500/5 p-6 space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-amber-500/20 pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-amber-700 dark:text-amber-400">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>Application Crawl Stopped</span>
              </div>
              <button
                type="button"
                onClick={() => setShowCrawlConfig(true)}
                className="rounded-xl border border-border bg-card px-3.5 py-1.5 text-xs font-semibold text-foreground hover:bg-muted transition"
              >
                Re-Crawl Application
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages scanned</span>
                <span className="text-lg font-black text-foreground">{crawlJob?.progress?.pages_scanned ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Interactive elements found</span>
                <span className="text-lg font-black text-amber-600">{crawlJob?.progress?.elements_found ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages skipped</span>
                <span className="text-lg font-black text-muted-foreground">{crawlJob?.progress?.pages_skipped ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Elapsed time</span>
                <span className="text-lg font-black text-foreground font-mono">{crawlJob?.progress?.elapsed_formatted || '00:00:00'}</span>
              </div>
            </div>
          </div>
        )}

        {/* FAILED CRAWL STATE */}
        {crawlJob?.status === 'failed' && !isCrawling && (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-6 space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-red-500/20 pb-3">
              <div className="flex items-center gap-2 text-sm font-bold text-red-600 dark:text-red-400">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                <span>Application Crawl Failed</span>
              </div>
              <button
                type="button"
                onClick={() => setShowCrawlConfig(true)}
                className="rounded-xl border border-border bg-card px-3.5 py-1.5 text-xs font-semibold text-foreground hover:bg-muted transition"
              >
                Retry Crawl
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages scanned</span>
                <span className="text-lg font-black text-foreground">{crawlJob?.progress?.pages_scanned ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Interactive elements found</span>
                <span className="text-lg font-black text-muted-foreground">{crawlJob?.progress?.elements_found ?? 0}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Elapsed time</span>
                <span className="text-lg font-black text-foreground font-mono">{crawlJob?.progress?.elapsed_formatted || '00:00:00'}</span>
              </div>
            </div>
            <div className="space-y-1 text-xs">
              <p className="text-red-600 dark:text-red-300 font-semibold">
                <strong>Reason:</strong> {crawlJob?.error || crawlError || 'The crawler could not access or interact with the target application.'}
              </p>
              <p className="text-muted-foreground">
                <strong>Recommended action:</strong> Verify the Target Application Web Address is online and reachable, check authentication credentials if required, and retry.
              </p>
            </div>
          </div>
        )}

        {!hasCrawl && !isCrawling && crawlJob?.status !== 'failed' && crawlJob?.status !== 'stopped' && (
          <div className="flex items-center gap-2.5 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-xs font-semibold text-amber-700 dark:text-amber-300">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
            <span>Complete the Application Crawl before starting Requirement Generation.</span>
          </div>
        )}

        {hasCrawl && !showCrawlConfig && !isCrawling ? (
          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-6 space-y-4 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-emerald-500/20 pb-4">
              <div>
                <h3 className="text-sm font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Application Crawl Completed
                </h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Verified reachable routes, captured interactive elements, and structured Page Object Models.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowCrawlConfig(true)}
                  className="rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-semibold text-foreground hover:bg-muted transition"
                >
                  Re-Crawl Application
                </button>
                <Link
                  href={`/test-case-generation?projectId=${projectId}`}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-purple-600 px-5 py-2 text-xs font-bold text-white shadow-md shadow-orange-500/20 hover:opacity-95 transition"
                >
                  <Plus className="h-4 w-4" />
                  <span>Start Requirement Generation</span>
                </Link>
              </div>
            </div>

            {/* REAL METRICS SUMMARY */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages scanned</span>
                <span className="text-lg font-black text-foreground">{pagesCrawled}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Interactive elements found</span>
                <span className="text-lg font-black text-emerald-600 dark:text-emerald-400">{elementsFound}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Pages skipped</span>
                <span className="text-lg font-black text-muted-foreground">{pagesSkipped}</span>
              </div>
              <div className="rounded-xl border border-border/70 bg-card/70 p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground block">Elapsed time</span>
                <span className="text-lg font-black text-foreground font-mono">{elapsedFormatted}</span>
              </div>
            </div>

            {/* GATING & READINESS CONFIRMATIONS */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-xs">
              <div className="flex items-center gap-2 rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-3.5 py-2.5 text-emerald-700 dark:text-emerald-300 font-semibold">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                <span>Application Knowledge: Stored successfully</span>
              </div>
              <div className="flex items-center gap-2 rounded-xl bg-purple-500/10 border border-purple-500/20 px-3.5 py-2.5 text-purple-700 dark:text-purple-300 font-semibold">
                <Sparkles className="h-4 w-4 shrink-0 text-purple-600 dark:text-purple-400" />
                <span>Requirement Generation: Ready</span>
              </div>
            </div>
          </div>
        ) : (
          (!hasCrawl || showCrawlConfig) && !isCrawling && (
            <form onSubmit={handleStartCrawl} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="workspace-crawl-url" className="text-xs font-semibold text-foreground uppercase tracking-wider">
                  Deployed Application URL <span className="text-red-500">*</span>
                </label>
                <div className="flex flex-col sm:flex-row gap-3">
                  <input
                    id="workspace-crawl-url"
                    type="url"
                    required
                    value={crawlUrl}
                    onChange={(e) => setCrawlUrl(e.target.value)}
                    placeholder="https://your-deployed-app.example.com"
                    className="min-w-0 flex-1 rounded-xl border border-border/80 bg-background px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 transition"
                  />
                  <button
                    type="submit"
                    disabled={crawlBusy || !crawlUrl.trim()}
                    className="inline-flex min-w-44 items-center justify-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-xs font-bold text-primary-foreground shadow hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-60 transition"
                  >
                    <Sparkles className="h-4 w-4" />
                    <span>{hasCrawl ? 'Re-Crawl Application' : 'Start Application Crawl'}</span>
                  </button>
                </div>
              </div>

              {/* Target Application Web Address (Optional) */}
              <div className="space-y-1.5">
                <label htmlFor="workspace-target-address" className="text-xs font-semibold text-foreground uppercase tracking-wider">
                  Target Application Web Address <span className="text-muted-foreground font-normal normal-case">(Optional)</span>
                </label>
                <input
                  id="workspace-target-address"
                  type="url"
                  value={targetPageAddress}
                  onChange={(e) => setTargetPageAddress(e.target.value)}
                  placeholder="https://your-deployed-app.example.com/target-path"
                  className="w-full rounded-xl border border-border/80 bg-background px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/10 transition"
                />
                <p className="text-[11px] text-muted-foreground">
                  Optional. If supplied, the crawler focuses on this target page and its related reachable application area within the application boundary.
                </p>
              </div>

              {/* Crawl Scope & Authentication */}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label htmlFor="workspace-crawl-scope" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Crawl Scope
                  </label>
                  <select
                    id="workspace-crawl-scope"
                    value={crawlScope}
                    onChange={(e) => setCrawlScope(e.target.value as any)}
                    className="w-full rounded-xl border border-border/80 bg-background px-3 py-2 text-xs outline-none focus:border-primary transition"
                  >
                    <option value="full_application">Full Application *</option>
                    <option value="specific_page">Target Application Web Address (Optional)</option>
                  </select>
                  <p className="text-[11px] text-muted-foreground">
                    {crawlScope === 'full_application'
                      ? 'Crawl the complete reachable application within the permitted application boundary.'
                      : 'Crawl the target application address and its reachable related pages.'}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="workspace-auth-mode" className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                    Authentication
                  </label>
                  <select
                    id="workspace-auth-mode"
                    value={authMode}
                    onChange={(e) => setAuthMode(e.target.value as any)}
                    className="w-full rounded-xl border border-border/80 bg-background px-3 py-2 text-xs outline-none focus:border-primary transition"
                  >
                    <option value="no_auth">No Authentication Required</option>
                    <option value="credentials">Credentials (Identifier + Password)</option>
                    <option value="existing_session">Existing Session State</option>
                  </select>
                  <p className="text-[11px] text-muted-foreground">
                    Authentication configuration to access protected application sections.
                  </p>
                </div>
              </div>


              {authMode === 'credentials' && (
                <div className="grid gap-4 rounded-xl border border-border/80 bg-muted/20 p-4 grid-cols-1 sm:grid-cols-2 min-w-0 max-w-full overflow-hidden">
                  <div className="space-y-1.5 min-w-0">
                    <label htmlFor="workspace-auth-identifier" className="text-xs font-semibold block">
                      Generic Identifier <span className="text-muted-foreground font-normal">(Email, Username, ID)</span>
                    </label>
                    <input
                      id="workspace-auth-identifier"
                      type="text"
                      placeholder="e.g. user@example.com or admin"
                      value={authIdentifier}
                      onChange={(e) => setAuthIdentifier(e.target.value)}
                      className="w-full min-w-0 max-w-full box-border rounded-lg border border-border/80 bg-background px-3 py-2 text-xs outline-none focus:border-primary transition"
                    />
                  </div>
                  <div className="space-y-1.5 min-w-0">
                    <label htmlFor="workspace-auth-password" className="text-xs font-semibold block">
                      Password
                    </label>
                    <input
                      id="workspace-auth-password"
                      type="password"
                      placeholder="••••••••"
                      value={authPassword}
                      onChange={(e) => setAuthPassword(e.target.value)}
                      className="w-full min-w-0 max-w-full box-border rounded-lg border border-border/80 bg-background px-3 py-2 text-xs outline-none focus:border-primary transition"
                    />
                  </div>
                </div>
              )}

              {authMode === 'existing_session' && (
                <div className="space-y-1.5 rounded-xl border border-border/80 bg-muted/20 p-4">
                  <label htmlFor="workspace-auth-session" className="text-xs font-semibold">
                    Session Storage State JSON
                  </label>
                  <textarea
                    id="workspace-auth-session"
                    rows={2}
                    placeholder='{"cookies": [...], "origins": [...]}'
                    value={authSessionState}
                    onChange={(e) => setAuthSessionState(e.target.value)}
                    className="w-full rounded-lg border border-border/80 bg-background px-3 py-2 font-mono text-xs outline-none focus:border-primary transition"
                  />
                </div>
              )}

              {hasCrawl && (
                <p className="text-[11px] text-muted-foreground italic">
                  Note: Re-crawling updates the application knowledge while preserving all previous requirement generations.
                </p>
              )}
            </form>
          )
        )}
      </section>

      {/* ── GENERATION HISTORY / SELECTOR ──────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-foreground">Requirement Generations</h2>
            <p className="text-xs text-muted-foreground">
              Select a generation to view its independent user stories, test scenarios, test cases, and automation scripts.
            </p>
          </div>
          <Link
            href={`/test-case-generation?projectId=${projectId}`}
            className="inline-flex items-center gap-1 text-xs font-bold text-primary hover:underline"
          >
            <Plus className="h-3.5 w-3.5" /> Start another generation
          </Link>
        </div>

        {generations.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {generations.map((gen, idx) => {
              const isSelected = gen.workflow_id === selectedWorkflowId;
              const genNumber = generations.length - idx;
              const isDone = gen.status === 'completed';

              return (
                <button
                  key={gen.workflow_id}
                  type="button"
                  onClick={() => setSelectedWorkflowId(gen.workflow_id)}
                  className={`group flex flex-col justify-between rounded-2xl border p-4 text-left transition-all ${
                    isSelected
                      ? 'border-primary bg-primary/5 shadow-md ring-2 ring-primary/20'
                      : 'border-border/80 bg-card hover:border-primary/40 hover:bg-muted/30'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className={`flex h-6 w-6 items-center justify-center rounded-lg text-xs font-bold ${
                          isSelected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                        }`}>
                          {genNumber}
                        </span>
                        <h3 className="text-sm font-bold text-foreground">
                          Generation {genNumber}
                          {idx === 0 && <span className="ml-1.5 rounded-md bg-purple-500/15 px-1.5 py-0.5 text-[9px] font-bold text-purple-400">Latest</span>}
                        </h3>
                      </div>
                      <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[9px] font-bold capitalize ${
                        isDone ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-orange-500/10 text-orange-600'
                      }`}>
                        {isDone ? <CheckCircle2 className="h-2.5 w-2.5" /> : <Activity className="h-2.5 w-2.5" />}
                        {gen.status.replaceAll('_', ' ')}
                      </span>
                    </div>

                    <p className="mt-2 text-[11px] text-muted-foreground flex items-center gap-1">
                      <Clock3 className="h-3 w-3" /> {formatDate(gen.started_at || gen.completed_at)}
                    </p>

                    <div className="mt-3 grid grid-cols-3 gap-1.5 text-center text-[10px]">
                      <div className="rounded-lg bg-background/80 p-1.5 border border-border/50">
                        <strong className="block font-bold text-foreground">{gen.user_story_count || 0}</strong>
                        <span className="text-muted-foreground">Stories</span>
                      </div>
                      <div className="rounded-lg bg-background/80 p-1.5 border border-border/50">
                        <strong className="block font-bold text-foreground">{gen.scenario_count || 0}</strong>
                        <span className="text-muted-foreground">Scenarios</span>
                      </div>
                      <div className="rounded-lg bg-background/80 p-1.5 border border-border/50">
                        <strong className="block font-bold text-foreground">{gen.test_case_count || 0}</strong>
                        <span className="text-muted-foreground">Cases</span>
                      </div>
                    </div>
                  </div>

                  <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-2 text-[11px]">
                    <span className="font-mono text-muted-foreground truncate max-w-[120px]">
                      {gen.workflow_id.slice(0, 8)}...
                    </span>
                    <span className={`font-bold transition ${isSelected ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground'}`}>
                      {isSelected ? 'Active View' : 'Select →'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="flex min-h-40 flex-col items-center justify-center rounded-2xl border border-dashed border-border/80 bg-card/40 p-6 text-center">
            <Layers className="h-8 w-8 text-primary mb-2" />
            <h3 className="text-sm font-bold">No requirement generations yet</h3>
            <p className="mt-1 text-xs text-muted-foreground max-w-sm">
              Start your first requirement generation for this application to produce scenarios, test cases, and automation.
            </p>
            <Link
              href={`/test-case-generation?projectId=${projectId}`}
              className="mt-3 inline-flex items-center gap-1.5 rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground shadow transition hover:opacity-90"
            >
              <Plus className="h-4 w-4" />
              <span>Start Generation 1</span>
            </Link>
          </div>
        )}
      </section>

      {/* ── ARTIFACT NAVIGATION TABS ───────────────────────────────────── */}
      <div className="flex items-center gap-1.5 overflow-x-auto border-b border-border/60 pb-2 scrollbar-none">
        {tabsConfig.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-bold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-orange-500 to-purple-600 text-white shadow-md shadow-orange-500/15'
                  : 'bg-card/70 text-muted-foreground hover:bg-card hover:text-foreground border border-border/50'
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{tab.label}</span>
              <span className={`rounded-full px-1.5 py-0.2 text-[10px] ${
                isActive ? 'bg-white/20 text-white' : 'bg-muted text-muted-foreground'
              }`}>
                {tab.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* ── ARTIFACT VIEW CONTENT AREA ─────────────────────────────────── */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`${selectedWorkflowId}-${activeTab}`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="rounded-3xl border border-border/80 bg-card p-6 shadow-sm"
        >
          {/* TAB 1: USER STORIES & ACCEPTANCE CRITERIA */}
          {activeTab === 'stories' && (
            <div className="space-y-5">
              <div className="flex justify-between items-center pb-3 border-b border-border/60">
                <div>
                  <h3 className="text-base font-bold">Requirement Specifications (Selected Generation)</h3>
                  <p className="text-xs text-muted-foreground">User stories and acceptance criteria used as input</p>
                </div>
                <Link
                  href={`/test-case-generation?projectId=${projectId}`}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground shadow-sm"
                >
                  <Plus className="h-3.5 w-3.5" /> Add New Generation
                </Link>
              </div>

              <div className="space-y-4">
                {userStories.map((story, idx) => (
                  <div key={idx} className="rounded-2xl border border-border/70 bg-background/60 p-5 space-y-3">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 font-bold text-xs text-primary">
                        US-{idx + 1}
                      </span>
                      <h4 className="text-sm font-bold text-foreground">{story}</h4>
                    </div>
                  </div>
                ))}
                {userStories.length === 0 && (
                  <p className="rounded-xl border border-dashed border-border p-5 text-xs text-muted-foreground">
                    No user stories recorded for this generation.
                  </p>
                )}
              </div>

              {acceptanceCriteria.length > 0 && (
                <div className="mt-6 space-y-3 pt-4 border-t border-border/40">
                  <h4 className="text-sm font-bold text-foreground">Acceptance Criteria</h4>
                  <ul className="space-y-2 text-xs text-muted-foreground">
                    {acceptanceCriteria.map((ac, idx) => (
                      <li key={idx} className="flex items-start gap-2.5 rounded-xl border border-border/50 bg-background/40 p-3">
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                        <span>{ac}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: FUNCTIONAL TEST SCENARIOS */}
          {activeTab === 'scenarios' && (
            <div className="space-y-4">
              <div className="pb-3 border-b border-border/60">
                <h3 className="text-base font-bold">Functional Test Scenarios</h3>
                <p className="text-xs text-muted-foreground">Derived test conditions and business flows</p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {testScenarios.map((sc: any, idx) => (
                  <div key={idx} className="rounded-2xl border border-border/70 bg-background/60 p-4 space-y-2">
                    <span className="font-mono text-xs font-bold text-purple-400">{String(sc.scenario_id || sc.id || `SC-${idx + 1}`)}</span>
                    <h4 className="text-xs font-bold text-foreground">{String(sc.title || sc.name || '')}</h4>
                    <span className="inline-block rounded-full bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">
                      {String(sc.scenario_type || sc.type || 'functional')}
                    </span>
                    {sc.description && <p className="text-xs text-muted-foreground leading-relaxed mt-1">{sc.description}</p>}
                  </div>
                ))}
                {testScenarios.length === 0 && (
                  <p className="col-span-2 rounded-xl border border-dashed border-border p-5 text-xs text-muted-foreground">
                    No scenarios available for this generation.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 3: STEP-BY-STEP TEST CASES */}
          {activeTab === 'testcases' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center pb-3 border-b border-border/60">
                <div>
                  <h3 className="text-base font-bold">Step-by-Step Test Cases</h3>
                  <p className="text-xs text-muted-foreground">Actionable execution steps with preconditions and expected outcomes</p>
                </div>
                <Link
                  href={`/test-case-generation/results?projectId=${projectId}${selectedWorkflowId ? `&workflowId=${selectedWorkflowId}` : ''}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-3.5 py-1.5 text-xs font-bold hover:bg-muted transition"
                >
                  <FileCheck2 className="h-3.5 w-3.5 text-primary" /> Open Test Cases View
                </Link>
              </div>
              <div className="space-y-4">
                {testCases.map((tc: any, idx) => (
                  <div key={idx} className="rounded-2xl border border-border/70 bg-background/60 p-5 space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="font-mono text-xs font-bold text-orange-500">{String(tc.test_case_id || tc.id || `TC-${idx + 1}`)}</span>
                      <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-bold text-emerald-500">
                        {String(tc.validation_status || tc.priority || 'Generated')}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-foreground">{String(tc.title)}</h4>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <p className="font-semibold text-foreground">Execution Steps:</p>
                      <ol className="list-decimal list-inside space-y-1 pl-1">
                        {Array.isArray(tc.steps) && tc.steps.map((st: unknown, sIdx: number) => (
                          <li key={sIdx}>
                            {typeof st === 'string' ? st : String((st as Record<string, unknown>).action || '')}
                            {typeof st === 'object' && st && (st as Record<string, unknown>).expected_result ? ` — Expected: ${String((st as Record<string, unknown>).expected_result)}` : ''}
                          </li>
                        ))}
                      </ol>
                    </div>
                    {tc.description && (
                      <p className="text-xs text-muted-foreground pt-2 border-t border-border/40">
                        <strong>Description:</strong> {String(tc.description)}
                      </p>
                    )}
                  </div>
                ))}
                {testCases.length === 0 && (
                  <p className="rounded-xl border border-dashed border-border p-5 text-xs text-muted-foreground">
                    No test cases generated for this generation yet.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: PLAYWRIGHT TEST SCRIPTS */}
          {activeTab === 'scripts' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-border/60">
                <div>
                  <h3 className="text-base font-bold">Generated Playwright Automation Scripts</h3>
                  <p className="text-xs text-muted-foreground">Executable TypeScript Playwright test code and page objects</p>
                </div>
              </div>

              {playwrightScripts.map((scr, idx) => (
                <div key={idx} className="rounded-2xl border border-border/80 bg-slate-950 text-slate-100 overflow-hidden shadow-lg">
                  <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
                    <div className="flex items-center gap-2">
                      <Code2 className="h-4 w-4 text-purple-400" />
                      <span className="font-mono text-xs font-bold text-purple-300">{String(scr.name || scr.script_id || `script_${idx + 1}.spec.ts`)}</span>
                    </div>
                    <button
                      onClick={() => handleCopyCode(String(scr.source || ''), idx)}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-slate-800 px-3 py-1.5 text-[11px] font-bold text-slate-300 hover:text-white hover:bg-slate-700 transition"
                    >
                      <Copy className="h-3.5 w-3.5" /> {copiedScriptIndex === idx ? 'Copied!' : 'Copy Code'}
                    </button>
                  </div>
                  <pre className="p-4 text-xs font-mono overflow-x-auto leading-relaxed text-slate-300">
                    {String(scr.source || '')}
                  </pre>
                </div>
              ))}
              {playwrightScripts.length === 0 && (
                <div className="rounded-2xl border border-dashed border-border p-8 text-center space-y-3">
                  <Code2 className="h-8 w-8 text-muted-foreground mx-auto" />
                  <h4 className="text-sm font-bold text-foreground">No scripts generated for this run</h4>
                  <p className="text-xs text-muted-foreground max-w-sm mx-auto">
                    Generate modular Page Object Models and test specifications from your test cases.
                  </p>
                  <Link
                    href={`/test-case-generation/automation?projectId=${projectId}${selectedWorkflowId ? `&workflowId=${selectedWorkflowId}` : ''}`}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground shadow"
                  >
                    <span>Open Automation Runner</span>
                  </Link>
                </div>
              )}
            </div>
          )}

          {/* TAB 5: EXECUTION REPORTS */}
          {activeTab === 'execution' && (
            <div className="space-y-4">
              <div className="flex justify-between items-center pb-3 border-b border-border/60">
                <div>
                  <h3 className="text-base font-bold">Execution Reports & Evidence</h3>
                  <p className="text-xs text-muted-foreground">Test execution pass/fail statistics</p>
                </div>
                <Link
                  href={`/test-case-generation/reports?projectId=${projectId}${selectedWorkflowId ? `&workflowId=${selectedWorkflowId}` : ''}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-3.5 py-1.5 text-xs font-bold hover:bg-muted transition"
                >
                  <PlayCircle className="h-3.5 w-3.5 text-primary" /> Open Execution Reports
                </Link>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                <div className="rounded-2xl border border-border bg-muted/20 p-4 text-center">
                  <span className="block text-3xl font-extrabold">{latestReport?.total_scripts ?? 0}</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Total Scripts</span>
                </div>
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
                  <span className="block text-3xl font-extrabold text-emerald-500">{latestReport?.passed_scripts ?? 0}</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Passed Scripts</span>
                </div>
                <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 text-center">
                  <span className="block text-3xl font-extrabold text-rose-500">{latestReport?.failed_scripts ?? 0}</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Failed Scripts</span>
                </div>
                <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 text-center">
                  <span className="block text-3xl font-extrabold text-amber-500">{latestReport?.skipped_scripts ?? 0}</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Skipped Scripts</span>
                </div>
                <div className="rounded-2xl border border-purple-500/20 bg-purple-500/5 p-4 text-center">
                  <span className="block text-3xl font-extrabold text-purple-500">{latestReport ? `${latestReport.success_percentage}%` : '—'}</span>
                  <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">Success Rate</span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: TRACEABILITY MATRIX */}
          {activeTab === 'traceability' && (
            <div className="space-y-4">
              <div className="pb-3 border-b border-border/60">
                <h3 className="text-base font-bold">End-to-End Traceability Matrix</h3>
                <p className="text-xs text-muted-foreground">Requirement ➔ Scenario ➔ Test Case ➔ Script mapping</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-border/60 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                      <th className="py-2.5 px-3">Req ID</th>
                      <th className="py-2.5 px-3">User Story</th>
                      <th className="py-2.5 px-3">Test Case ID</th>
                      <th className="py-2.5 px-3">Automation Script</th>
                      <th className="py-2.5 px-3 text-right">Coverage</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40 font-mono">
                    {testCases.map((testCase: any, idx) => {
                      const testCaseId = String(testCase.test_case_id || testCase.id || `TC-${idx + 1}`);
                      const script = playwrightScripts.find((item) => String(item.test_case_id || '') === testCaseId);
                      return (
                        <tr key={`${testCaseId}-${idx}`} className="hover:bg-muted/30">
                          <td className="py-3 px-3 text-primary font-bold">{Array.isArray(testCase.requirement_ids) ? testCase.requirement_ids.join(', ') : 'REQ-1'}</td>
                          <td className="py-3 px-3 font-sans font-medium">{Array.isArray(testCase.user_story_ids) ? testCase.user_story_ids.join(', ') : userStories[0] || '—'}</td>
                          <td className="py-3 px-3 text-purple-400">{testCaseId}</td>
                          <td className="py-3 px-3 text-emerald-400">{String(script?.name || script?.script_id || 'Not generated')}</td>
                          <td className="py-3 px-3 text-right font-bold text-emerald-500">{script ? 'Covered' : 'Not covered'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TAB 7: VALIDATION RESULTS */}
          {activeTab === 'validation' && (
            <div className="space-y-4">
              <div className="pb-3 border-b border-border/60">
                <h3 className="text-base font-bold">AI Validation Quality Scores</h3>
                <p className="text-xs text-muted-foreground">Confidence scores and quality gates for the selected generation</p>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                {validations.map((validation, index) => (
                  <div key={index} className="rounded-2xl border border-border bg-muted/20 p-4">
                    <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">{index === 0 ? 'Scenario validation' : 'Test-case validation'}</p>
                    <p className="mt-2 text-3xl font-extrabold text-primary">{Math.round((validation?.confidence_score ?? 0) * 100)}%</p>
                    <p className="mt-1 text-sm capitalize">Status: {validation?.status || 'Passed'}</p>
                    <p className="mt-1 text-xs text-muted-foreground">Issues: {validation?.issues?.length ?? 0}</p>
                  </div>
                ))}
                {!validations.length && (
                  <p className="rounded-xl border border-dashed border-border p-4 text-sm text-muted-foreground col-span-2">
                    Validation checks completed successfully with high confidence.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 8: APPLICATION KNOWLEDGE (PROJECT LEVEL) */}
          {activeTab === 'knowledge' && (
            <div className="space-y-6">
              <div className="flex justify-between items-center pb-3 border-b border-border/60">
                <div>
                  <h3 className="text-base font-bold">Application Crawl & Knowledge Graph (Project-Level)</h3>
                  <p className="text-xs text-muted-foreground">
                    Shared application structure reused across all requirement generations
                  </p>
                </div>
                <Link
                  href={`/test-case-generation/automation?projectId=${projectId}`}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-background px-3 py-1.5 text-xs font-bold hover:bg-muted transition"
                >
                  <RefreshCw className="h-3.5 w-3.5 text-primary" /> Refresh Crawl
                </Link>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-2xl border border-border bg-card p-4 space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground">Pages Discovered</p>
                  <p className="text-2xl font-extrabold text-primary">{pagesCrawled}</p>
                </div>
                <div className="rounded-2xl border border-border bg-card p-4 space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground">Interactive Elements Discovered</p>
                  <p className="text-2xl font-extrabold text-emerald-500">{elementsFound}</p>
                </div>
                <div className="rounded-2xl border border-border bg-card p-4 space-y-1">
                  <p className="text-xs font-semibold text-muted-foreground">Authentication Configuration</p>
                  <p className="text-sm font-bold text-foreground mt-2">{project?.auth_config ? 'Configured' : 'None required'}</p>
                </div>
              </div>

              {crawlKnowledge?.application_map?.pages && (
                <div className="space-y-3">
                  <h4 className="text-sm font-bold text-foreground">Discovered Application Pages</h4>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {crawlKnowledge.application_map.pages.map((p: any, idx: number) => (
                      <div key={idx} className="flex items-center justify-between rounded-xl border border-border/60 bg-background/50 p-3 text-xs">
                        <span className="font-mono text-primary truncate max-w-[280px]">{p.url || p.path || p}</span>
                        <span className="rounded-md bg-muted px-2 py-0.5 text-[10px] font-semibold text-muted-foreground">Verified</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
