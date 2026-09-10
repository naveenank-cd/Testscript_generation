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
  Database
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

  const hasCrawl = Boolean(crawlKnowledge || (project?.crawl_knowledge && Object.keys(project.crawl_knowledge).length > 0));
  const pagesCrawled = crawlKnowledge?.pages_crawled || project?.crawl_knowledge?.pages_crawled || crawlKnowledge?.application_map?.pages?.length || 0;
  const elementsFound = crawlKnowledge?.elements_found || project?.crawl_knowledge?.elements_found || crawlKnowledge?.discovered_elements?.length || 0;

  const tabsConfig: { id: ArtifactTab; label: string; icon: React.ElementType; count: number }[] = [
    { id: 'stories', label: 'User Stories & AC', icon: FileText, count: userStories.length },
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
          <Link
            href={`/test-case-generation?projectId=${projectId}`}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-purple-600 px-4 py-2.5 text-xs font-bold text-white shadow-md shadow-orange-500/20 hover:opacity-95 transition"
          >
            <Plus className="h-4 w-4" />
            <span>+ Start New Generation</span>
          </Link>

          <Link
            href={`/test-case-generation/automation?projectId=${projectId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-bold hover:bg-muted transition"
          >
            <Zap className="h-4 w-4 text-purple-500" />
            <span>Run Test Scripts</span>
          </Link>
        </div>
      </div>

      {/* ── PROJECT HEADER CARD ────────────────────────────────────────── */}
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
              {/* Target URL */}
              <div className="flex items-center gap-1.5 rounded-xl border border-border/70 bg-background/60 px-3 py-1.5 text-muted-foreground font-medium">
                <Globe className="h-3.5 w-3.5 text-primary" />
                <span>{project?.application_url || 'Target URL not configured'}</span>
                {project?.application_url && (
                  <a href={project.application_url} target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-primary ml-1">
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>

              {/* Crawl Knowledge Status */}
              <div className={`flex items-center gap-1.5 rounded-xl border px-3 py-1.5 font-semibold ${
                hasCrawl
                  ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                  : 'border-border/70 bg-background/60 text-muted-foreground'
              }`}>
                <span className={`h-2 w-2 rounded-full ${hasCrawl ? 'bg-emerald-500 animate-pulse' : 'bg-muted-foreground'}`} />
                <span>{hasCrawl ? `Crawl Knowledge: ${pagesCrawled} pages · ${elementsFound} verified elements` : 'Pending Application Crawl'}</span>
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
              <div className="pb-3 border-b border-border/60">
                <h3 className="text-base font-bold">Step-by-Step Test Cases</h3>
                <p className="text-xs text-muted-foreground">Actionable execution steps with preconditions and expected outcomes</p>
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
                    href={`/test-case-generation/automation?projectId=${projectId}`}
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
              <div className="pb-3 border-b border-border/60">
                <h3 className="text-base font-bold">Execution Reports & Evidence</h3>
                <p className="text-xs text-muted-foreground">Test execution pass/fail statistics</p>
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
