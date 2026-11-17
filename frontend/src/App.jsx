import React, { lazy, Suspense, useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import "./ui-feedback.css";
import {
  Activity, ArrowDownRight, ArrowRight, ArrowUpRight, BookOpen, BriefcaseBusiness,
  Check, ChevronDown, CircleHelp, Compass, FileText, GraduationCap,
  LayoutDashboard, LoaderCircle, Menu, MessageSquareText, Network,
  PanelLeftClose, PanelLeftOpen, Sparkles, Target, UserRound, X,
} from "lucide-react";
import {
  analyze, errorMessage, extractSkills, getDashboard, getDatasetInfo, getHealth,
  getJobs, getModelInfo, getModelPerformance, getStudents, suggestProfile,
} from "./services/api.js";
const LandingPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.LandingPage })));
const StudentsPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.StudentsPage })));
const JobsPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.JobsPage })));
const ResourceCatalogPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.ResourceCatalogPage })));
const LearningPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.LearningPage })));
const ReportsPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.ReportsPage })));
const HistoryPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.HistoryPage })));
const AboutPage = lazy(() => import("./pages/ManagementPages.jsx").then((pages) => ({ default: pages.AboutPage })));
const CareerPages = lazy(() => import("./pages/CareerPages.jsx"));
const EvaluationBarChart = lazy(() => import("./ModelCharts.jsx").then((charts) => ({ default: charts.EvaluationBarChart })));
const RoleDistributionChart = lazy(() => import("./ModelCharts.jsx").then((charts) => ({ default: charts.RoleDistributionChart })));
const ModelF1Chart = lazy(() => import("./ModelCharts.jsx").then((charts) => ({ default: charts.ModelF1Chart })));

const featureFields = [
  ["cgpa", "CGPA", "0–10", 0, 10, 0.01],
  ["coding_skill_score", "Coding score", "0–100", 0, 100, 1],
  ["aptitude_score", "Aptitude score", "0–100", 0, 100, 1],
  ["communication_skill_score", "Communication", "0–100", 0, 100, 1],
  ["logical_reasoning_score", "Logical reasoning", "0–100", 0, 100, 1],
  ["mock_interview_score", "Mock interview", "0–100", 0, 100, 1],
  ["backlogs", "Backlogs", "count", 0, 100, 1],
  ["github_repos", "GitHub repositories", "count", 0, 100000, 1],
  ["internships_count", "Internships", "count", 0, 100, 1],
  ["projects_count", "Projects", "count", 0, 1000, 1],
];

const emptyForm = {
  student_id: "", student_name: "", email: "", job_id: "", algorithm: "SVM", cgpa: "", coding_skill_score: "", aptitude_score: "",
  communication_skill_score: "", logical_reasoning_score: "", mock_interview_score: "",
  backlogs: "", github_repos: "", internships_count: "", projects_count: "", branch: "",
  student_skills: "", job_title: "", company_name: "", role_category: "", location: "",
  work_mode: "", required_skills: "", job_description: "",
  experience_min_yrs: "", experience_max_yrs: "", is_fresher_friendly: "",
  job_url: "",
};

function studentFormFields(record) {
  const keys = ["student_id", "student_name", "email", "branch", "student_skills", ...featureFields.map(([key]) => key)];
  return Object.fromEntries(keys.map((key) => [key, record[key] == null ? "" : String(record[key])]));
}

function jobFormFields(record) {
  return {
    job_id: record.external_job_id || "", job_title: record.job_title, company_name: record.company_name,
    job_description: record.job_description, required_skills: record.required_skills,
    role_category: record.role_category, work_mode: record.work_mode, location: record.location,
    job_url: record.job_url, experience_min_yrs: record.experience_min_yrs,
    experience_max_yrs: record.experience_max_yrs,
    is_fresher_friendly: record.is_fresher_friendly == null ? "" : String(Boolean(record.is_fresher_friendly)),
  };
}

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/students", label: "Students", icon: UserRound },
  { to: "/jobs", label: "Jobs", icon: BriefcaseBusiness },
  { to: "/resources", label: "Resource catalogue", icon: BookOpen },
  { to: "/career", label: "Career intelligence", icon: Network },
  { to: "/workspace", label: "Match workspace", icon: Target },
  { to: "/learning", label: "Learning path", icon: Sparkles },
  { to: "/model-room", label: "Model comparison", icon: Activity },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/history", label: "Analysis history", icon: Activity },
  { to: "/about", label: "About project", icon: CircleHelp },
];

function App() {
  const [form, setForm] = useState(emptyForm);
  const [dataset, setDataset] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [health, setHealth] = useState(null);
  const [pageError, setPageError] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const location = useLocation();

  useEffect(() => {
    let live = true;
    let apiFailures = 0;
    getModelInfo().then((data) => { if (live) { setModelInfo(data); if (data.available_algorithms?.length) setForm((current) => ({ ...current, algorithm: data.available_algorithms.includes(current.algorithm) ? current.algorithm : data.available_algorithms[0] })); } }).catch(() => { apiFailures += 1; if (live && apiFailures >= 3) setPageError("Can't reach Flask yet. Start the backend to load dataset details and model status."); });
    getHealth().then((data) => { if (live) setHealth(data); }).catch(() => { apiFailures += 1; if (live && apiFailures >= 3) setPageError("Can't reach Flask yet. Start the backend to load dataset details and model status."); });
    getDatasetInfo().then((data) => { if (live) setDataset(data); }).catch(() => { apiFailures += 1; if (live) setPageError(apiFailures >= 3 ? "Can't reach Flask yet. Start the backend to load dataset details and model status." : "Dataset summary could not be loaded. Check that the CSV is in the project data folder."); }).finally(() => { if (live) setLoadingData(false); });
    getDashboard().then((data) => { if (live) setDashboard(data); }).catch(() => {});
    getModelPerformance().then((data) => { if (live) setPerformance(data); }).catch(() => {});
    return () => { live = false; };
  }, []);

  const title = ({ "/": "Dashboard", "/landing": "Welcome", "/students": "Student management", "/jobs": "Job management", "/resources": "Resource catalogue", "/career": "Career intelligence", "/analysis": "Job analysis", "/skill-matching": "Skill matching", "/skill-gaps": "Skill gap analysis", "/workspace": "Match workspace", "/predictions": "ML predictions", "/learning": "Learning recommendations", "/model-room": "Model comparison", "/reports": "Reports", "/history": "Analysis history", "/about": "About project" })[location.pathname] || "Placement Intelligence";
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));

  return (
    <div className={`app-shell ${collapsed ? "is-collapsed" : ""}`}>
      <aside className={`sidebar ${menuOpen ? "mobile-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark"><Compass size={19} strokeWidth={2.4} /></div>
          <div className="brand-copy"><strong>placement<span>.</span></strong><small>INTELLIGENCE STUDIO</small></div>
          <button className="icon-btn mobile-close" onClick={() => setMenuOpen(false)} aria-label="Close menu"><X size={18} /></button>
        </div>

        <div className="workspace-chip"><span className="workspace-dot" /> SRM · Placement lab <ChevronDown size={14} /></div>
        <div className="nav-label">WORKSPACE</div>
        <nav className="side-nav">
          {navItems.map(({ to, label, icon: Icon, end }) => <NavLink key={to} to={to} end={end} onClick={() => setMenuOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><Icon size={17} /><span>{label}</span>{label === "Match workspace" && <span className="nav-count">01</span>}</NavLink>)}
        </nav>

        <div className="nav-label lower-label">YOUR PROJECT</div>
        <div className="project-nav"><div className="project-icon"><GraduationCap size={17} /></div><div><strong>Campus outcomes</strong><span>Experimental · v1.0</span></div><span className="live-dot" /></div>
        <div className="sidebar-bottom">
          <div className="sidebar-note"><div className="note-glyph"><Sparkles size={15} /></div><div><strong>Designed for discovery</strong><p>Match real profile signals to role requirements.</p></div></div>
          <div className="profile-chip"><div className="profile-avatar">SR</div><div><strong>SRM workspace</strong><span>Local prototype</span></div><Menu size={16} /></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <button className="icon-btn mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu size={19} /></button>
          <button className="icon-btn collapse-btn" onClick={() => setCollapsed((v) => !v)} aria-label="Toggle sidebar">{collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}</button>
          <div className="crumb"><span>Studio</span><span className="crumb-slash">/</span><strong>{title}</strong></div>
          <div className="top-actions"><div className={`api-pill ${health?.model?.ready ? "connected" : "disconnected"}`} title={health?.model?.errors?.join("; ") || "Model artifacts and preprocessing are ready"}><span />{health?.model?.ready ? "Predictions ready" : "Predictions unavailable"}</div><div className="top-separator" /><button className="icon-btn help-btn" title="About this prototype"><CircleHelp size={18} /></button><div className="top-avatar">S</div></div>
        </header>

        <div className="page-wrap">
          {pageError && <div className="inline-alert"><Activity size={16} />{pageError}<button onClick={() => setPageError("")} aria-label="Dismiss"><X size={15} /></button></div>}
          <Suspense fallback={<div className="page-loading"><LoaderCircle className="spin" size={18} />Loading workspace…</div>}>
            <Routes>
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/" element={<Overview dataset={dataset} dashboard={dashboard} modelInfo={modelInfo} health={health} loading={loadingData} />} />
              <Route path="/students" element={<StudentsPage />} />
              <Route path="/jobs" element={<JobsPage />} />
              <Route path="/resources" element={<ResourceCatalogPage />} />
              <Route path="/career" element={<CareerPages />} />
              <Route path="/workspace" element={<Workspace form={form} update={update} dataset={dataset} modelInfo={modelInfo} health={health} />} />
              <Route path="/analysis" element={<Workspace form={form} update={update} dataset={dataset} modelInfo={modelInfo} health={health} />} />
              <Route path="/skill-matching" element={<Workspace form={form} update={update} dataset={dataset} modelInfo={modelInfo} health={health} />} />
              <Route path="/skill-gaps" element={<Workspace form={form} update={update} dataset={dataset} modelInfo={modelInfo} health={health} />} />
              <Route path="/predictions" element={<Workspace form={form} update={update} dataset={dataset} modelInfo={modelInfo} health={health} />} />
              <Route path="/learning" element={<LearningPage />} />
              <Route path="/model-room" element={<ModelRoom modelInfo={modelInfo} performance={performance} health={health} />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/about" element={<AboutPage />} />
            </Routes>
          </Suspense>
          <footer className="footer-line"><span>PLACEMENT INTELLIGENCE · RESEARCH PROTOTYPE</span><span>Built for transparent, data-aware matching <span className="footer-spark">✳</span></span></footer>
        </div>
      </main>
    </div>
  );
}

function PageHeading({ eyebrow, title, description, action }) {
  return <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark" />{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}

function Overview({ dataset, dashboard, modelInfo, health, loading }) {
  const metrics = modelInfo?.evaluation_metrics || [];
  const selectedModel = modelInfo?.selected_model;
  const selectedMetric = metrics.find((metric) => metric.model === selectedModel);
  const dataReady = Boolean(health?.model?.ready);
  const chartData = metrics.map((m) => ({ name: m.model, accuracy: m.accuracy_pct, f1: m.suitable_f1_pct }));
  const topGaps = dashboard?.top_skill_gaps || [];
  const maxGapCount = Math.max(1, ...topGaps.map((gap) => gap.count));
  return <>
    <PageHeading eyebrow="YOUR PLACEMENT COMMAND CENTER" title={<>Turn student signals<br className="desktop-break" /> into <span className="gradient-text">clearer direction.</span></>} description="Explore candidate profiles, compare skill fit, and understand what your model can—and cannot—say." action={<NavLink to="/workspace" className="primary-action"><Sparkles size={16} /> Start an analysis <ArrowRight size={16} /></NavLink>} />

    <section className="hero-strip">
      <div className="hero-copy"><div className="hero-kicker"><span className="pulse-ring" /> PLACEMENT SIGNALS · LIVE WORKSPACE</div><h2>From profile to<br /><em>possibility.</em></h2><p>Bring a student profile and a job requirement together. See the match, the gaps, and the evidence behind every result.</p><NavLink to="/workspace" className="hero-link">Open match workspace <ArrowRight size={15} /></NavLink></div>
      <div className="hero-art" aria-hidden="true"><div className="orb orb-back" /><div className="orb orb-front"><div className="orb-core"><Target size={31} /></div><span className="orbit orbit-one" /><span className="orbit orbit-two" /><span className="orbit-dot dot-one" /><span className="orbit-dot dot-two" /><span className="orbit-dot dot-three" /></div><div className="floating-tag tag-match"><span className="mini-check"><Check size={12} /></span><span><strong>Skill fit</strong><small>Evidence based</small></span></div><div className="floating-tag tag-gap"><span className="mini-star"><Sparkles size={12} /></span><span><strong>Next steps</strong><small>Skill gap map</small></span></div></div>
      <div className="hero-foot"><span>01 <i /> PROFILE</span><span>02 <i /> ROLE</span><span>03 <i /> INSIGHT</span></div>
    </section>

    <div className="section-bar"><div><h2>Workspace pulse</h2><p>What’s available in this local project right now.</p></div><span className="updated-label"><span /> DATASET CONNECTED</span></div>
    <section className="stat-grid">
      <StatCard icon={UserRound} label="Unique source students" value={dataset ? dataset.students.toLocaleString() : "—"} note={dataset ? `Across ${dataset.rows.toLocaleString()} student–job rows` : loading ? "Reading local dataset…" : "Dataset unavailable"} tint="violet" source="CSV" />
      <StatCard icon={BriefcaseBusiness} label="Unique source jobs" value={dataset ? dataset.jobs.toLocaleString() : "—"} note={dataset ? `${dataset.role_categories.length} observed role categories` : "From the supplied CSV"} tint="blue" source="CSV" />
      <StatCard icon={Activity} label="Analyses saved" value={dashboard ? dashboard.total_analyses.toLocaleString() : "—"} note="SQLite analysis history" tint="blue" source="SQLite" />
      <StatCard icon={Target} label="Average skill match" value={dashboard?.average_skill_match_pct == null ? "—" : `${dashboard.average_skill_match_pct}%`} note={dashboard?.total_analyses ? "From saved analyses" : "Appears after the first analysis"} tint="mint" source="SQLite" />
      <StatCard icon={Check} label="Suitable / unsuitable" value={dashboard ? `${dashboard.suitable_predictions} / ${dashboard.unsuitable_predictions}` : "—"} note="Saved model outputs only" tint="amber" source="Model outputs" />
      <StatCard icon={Target} label="CV-selected model" value={selectedModel || "Unavailable"} note={selectedMetric ? `Held-out suitable F1 ${selectedMetric.suitable_f1_pct.toFixed(2)}% · grouped run` : "No verified training selection recorded"} tint="mint" source="Colab" />
      <StatCard icon={Activity} label="Prediction engine" value={dataReady ? "Ready" : "Unavailable"} note={dataReady ? "Artifacts and category encoding verified" : "Model artifacts or encoding verification is missing"} tint="amber" status={!dataReady} source={dataReady ? "Ready" : undefined} />
    </section>

    <div className="dashboard-grid">
      <section className="panel chart-panel"><div className="panel-heading"><div><span className="panel-kicker">COLAB EVALUATION</span><h3>Model comparison</h3><p>Test metrics from the notebook’s grouped split.</p></div><NavLink to="/model-room" className="text-link">Full report <ArrowRight size={14} /></NavLink></div>{chartData.length ? <div className="chart-wrap"><Suspense fallback={<div className="page-loading">Loading evaluation chart…</div>}><EvaluationBarChart data={chartData}/></Suspense></div> : <EmptyPanel text="Colab evaluation metrics are not available." />}
        <div className="chart-legend"><span><i className="legend-lilac" /> Accuracy</span><span><i className="legend-purple" /> Suitable-class F1</span><span className="legend-context">F1 highlights performance on the minority suitable class.</span></div>
      </section>
      <section className="panel dataset-panel"><div className="panel-heading"><div><span className="panel-kicker">DATA LANDSCAPE</span><h3>What’s in the dataset</h3><p>Role distribution across the supplied CSV.</p></div><div className="panel-icon"><FileText size={16} /></div></div>{dataset ? <><div className="dataset-total"><strong>{dataset.rows.toLocaleString()}</strong><span>student–job records</span></div><div className="data-mix"><div className="mix-ring"><Suspense fallback={<div className="page-loading">Loading role chart…</div>}><RoleDistributionChart data={Object.entries(dataset.category_counts.role_category).map(([name,value])=>({name,value}))} roles={dataset.role_categories.length}/></Suspense></div><div className="mix-details"><div><span className="mix-dot purple-dot" />{dataset.students.toLocaleString()} unique students</div><div><span className="mix-dot gray-dot" />{dataset.branches.length} branches</div><div><span className="mix-dot blue-dot" />{dataset.work_modes.length} work modes</div></div></div><div className="category-cloud">{dataset.role_categories.map((role) => <span key={role}>{role}</span>)}</div></> : <EmptyPanel text={loading ? "Loading dataset summary…" : "Dataset summary unavailable."} />}</section>
    </div>

    <section className="activity-grid"><article className="panel activity-panel"><div className="panel-heading"><div><span className="panel-kicker">PERSISTED ACTIVITY</span><h3>Recent analyses</h3><p>Saved records from the SQLite database.</p></div><NavLink to="/history" className="text-link">History <ArrowRight size={13} /></NavLink></div>{dashboard?.recent_analyses?.length ? dashboard.recent_analyses.slice(0, 5).map((entry) => <div className="activity-row" key={entry.id}><span className="activity-index">#{entry.id}</span><div><strong>{entry.student_name || entry.student_id || "Candidate"}</strong><small>{entry.job_title || "Job analysis"} · {entry.role_category || "Uncategorized"}</small></div><b>{entry.skill_match_pct == null ? "—" : `${entry.skill_match_pct}%`}</b></div>) : <EmptyPanel text="No analyses have been saved yet." />}</article><article className="panel activity-panel"><div className="panel-heading"><div><span className="panel-kicker">LEARNING SIGNALS</span><h3>Frequent skill gaps</h3><p>Aggregated from saved analyses only.</p></div><NavLink to="/learning" className="text-link">Learning plan <ArrowRight size={13} /></NavLink></div>{topGaps.length ? topGaps.map((gap) => <div className="gap-row" key={gap.skill}><span>{gap.skill}</span><div><i style={{ width: `${gap.count / maxGapCount * 100}%` }} /></div><strong>{gap.count}</strong></div>) : <EmptyPanel text="No saved skill-gap data yet." />}</article></section>

    <section className="next-step-card"><div className="next-step-icon"><Compass size={20} /></div><div><span className="panel-kicker">READY TO EXPLORE?</span><h3>Build a candidate-to-role match</h3><p>Enter the student and job details. We calculate skill gaps and keep generated suggestions clearly marked for review.</p></div><NavLink to="/workspace" className="round-arrow"><ArrowRight size={18} /></NavLink></section>
    <div className="prototype-note"><CircleHelp size={15} /><span>Suitability labels in this project are synthetic. A model result is not a hiring decision or a guarantee of placement.</span></div>
  </>;
}

function StatCard({ icon: Icon, label, value, note, tint, status, source = "Source" }) {
  return <article className="stat-card"><div className="stat-topline"><span className={`stat-icon ${tint}`}><Icon size={17} /></span><span className={`stat-status ${status ? "warn" : ""}`}><i />{status ? "Needs attention" : source}</span></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-note">{note}</div></article>;
}

function EmptyPanel({ text }) { return <div className="empty-panel"><span><FileText size={19} /></span><p>{text}</p></div>; }

function Workspace({ form, update, dataset, modelInfo, health }) {
  const [busy, setBusy] = useState("");
  const [alert, setAlert] = useState("");
  const [success, setSuccess] = useState("");
  const [suggestion, setSuggestion] = useState(null);
  const [skillResult, setSkillResult] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [extraction, setExtraction] = useState(null);
  const [students, setStudents] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [studentRecordId, setStudentRecordId] = useState("");
  const [jobRecordId, setJobRecordId] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([getStudents({ limit: 500 }), getJobs({ limit: 500 })])
      .then(([studentData, jobData]) => {
        if (!active) return;
        setStudents(studentData.items || []);
        setJobs(jobData.items || []);
        const params = new URLSearchParams(window.location.search);
        const requestedStudent = params.get("student_record_id");
        const requestedJob = params.get("job_record_id");
        const studentRecord = studentData.items?.find((item) => String(item.id) === requestedStudent);
        const jobRecord = jobData.items?.find((item) => String(item.id) === requestedJob);
        if (studentRecord) {
          setStudentRecordId(String(studentRecord.id));
          Object.entries(studentFormFields(studentRecord)).forEach(([key, value]) => update(key, value));
        }
        if (jobRecord) {
          setJobRecordId(String(jobRecord.id));
          Object.entries(jobFormFields(jobRecord)).forEach(([key, value]) => update(key, value == null ? "" : String(value)));
        }
      })
      .catch((error) => { if (active) setAlert(`Saved records could not be loaded: ${errorMessage(error)}`); });
    return () => { active = false; };
  }, []);

  function loadStudentRecord(id) {
    setStudentRecordId(id);
    const record = students.find((item) => String(item.id) === id);
    if (!record) return;
    Object.entries(studentFormFields(record)).forEach(([key, value]) => update(key, value));
  }

  function loadJobRecord(id) {
    setJobRecordId(id);
    const record = jobs.find((item) => String(item.id) === id);
    if (!record) return;
    const fields = jobFormFields(record);
    Object.entries(fields).forEach(([key, value]) => update(key, value == null ? "" : String(value)));
  }

  const profileFields = [...featureFields.map(([key]) => key), "branch", "student_skills"];
  const profileFilled = profileFields.filter((key) => form[key] !== "").length;
  const progress = Math.round((profileFilled / profileFields.length) * 100);
  const experienceEligible = form.is_fresher_friendly === "" ? null : form.is_fresher_friendly === "true";

  async function findSuggestion() {
    setAlert(""); setSuccess(""); setBusy("suggest");
    const partial = {};
    featureFields.forEach(([key]) => { if (form[key] !== "") partial[key] = Number(form[key]); });
    if (form.branch) partial.branch = form.branch;
    if (form.student_skills) partial.student_skills = form.student_skills;
    try { setSuggestion(await suggestProfile(partial)); }
    catch (error) { setAlert(errorMessage(error)); }
    finally { setBusy(""); }
  }

  function applySuggestion() {
    if (!suggestion) return;
    const blanksOnly = { ...form };
    Object.entries(suggestion.suggested_fields).forEach(([key, value]) => {
      if (blanksOnly[key] === "") blanksOnly[key] = value == null ? "" : String(value);
    });
    Object.entries(blanksOnly).forEach(([key, value]) => update(key, value));
    setSuccess("Suggestions were copied into empty fields. Please review and edit them before submitting.");
  }

  async function runAnalysis(event) {
    event.preventDefault(); setAlert(""); setSuccess(""); setBusy("analysis"); setPrediction(null);
    const required = ["student_skills", "required_skills", "branch", "role_category", "work_mode", ...featureFields.map(([key]) => key)];
    const missing = required.filter((key) => form[key] === "");
    if (missing.length) { setAlert(`Complete these required fields first: ${missing.map((key) => key.replaceAll("_", " ")).join(", ")}.`); setBusy(""); return; }
    const stamp = Date.now().toString(36).toUpperCase();
    const studentId = form.student_id || `STU-${stamp}`;
    const jobId = form.job_id || `JOB-${stamp}`;
    if (!form.student_id) update("student_id", studentId);
    if (!form.job_id) update("job_id", jobId);
    try {
      const result = await analyze({
        ...(studentRecordId ? { student_record_id: Number(studentRecordId) } : {}),
        ...(jobRecordId ? { job_record_id: Number(jobRecordId) } : {}),
        ...Object.fromEntries(featureFields.map(([key]) => [key, Number(form[key])])),
        student_id: studentId, student_name: form.student_name, email: form.email, branch: form.branch,
        student_skills: form.student_skills, job_id: jobId, job_title: form.job_title,
        company_name: form.company_name, role_category: form.role_category, location: form.location,
        work_mode: form.work_mode, required_skills: form.required_skills,
        job_description: form.job_description, job_url: form.job_url,
        experience_min_yrs: form.experience_min_yrs, experience_max_yrs: form.experience_max_yrs,
        is_fresher_friendly: form.is_fresher_friendly, request_prediction: true, algorithm: form.algorithm,
      });
      const skills = result.matching;
      setSkillResult({ ...skills, match_percentage: skills.skill_match_pct, notice: skills.matching_method });
      const modelPrediction = result.predictions?.[form.algorithm];
      setPrediction(modelPrediction ? { ...modelPrediction, interpretation: Number(modelPrediction.predicted_label) === 1 ? "Positive synthetic suitability label" : "Negative synthetic suitability label", notice: "This is a model output for a synthetic target, not a real placement probability." } : null);
      if (result.prediction_error) setAlert(`Skill analysis saved as #${result.analysis_id}. Prediction unavailable: ${result.prediction_error}`);
      else setSuccess(`Analysis #${result.analysis_id} saved. Skill matching and model output are ready.`);
    } catch (error) {
      setAlert(errorMessage(error));
    } finally { setBusy(""); }
  }

  async function extractFromDescription() {
    setAlert(""); setBusy("extract");
    try {
      const result = await extractSkills(form.job_description);
      setExtraction(result);
      if (result.extracted_skills.length) update("required_skills", result.extracted_skills.join(", "));
    } catch (error) { setAlert(errorMessage(error)); }
    finally { setBusy(""); }
  }

  const jobTitleOptions = dataset?.popular_job_titles || [];
  const locationOptions = dataset?.popular_locations || [];
  const comparison = modelInfo?.evaluation_metrics || [];

  return <>
    <PageHeading eyebrow="CANDIDATE + ROLE ANALYSIS" title={<>Match signals,<br className="desktop-break" /> <span className="gradient-text">not assumptions.</span></>} description="Enter the source details, inspect data-based suggestions, and keep generated outputs separate from what you supplied." action={<div className="workspace-progress"><div className="progress-copy"><span>STUDENT PROFILE COMPLETION</span><strong>{progress}%</strong></div><div className="progress-line"><i style={{ width: `${progress}%` }} /></div></div>} />
    <div className="workspace-layout">
      <form className="form-stack" onSubmit={runAnalysis}>
        <section className="panel form-panel"><div className="form-section-title"><div className="section-index"><Network size={14} /></div><div><span className="panel-kicker">SAVED SQLITE RECORDS</span><h2>Load a profile and job</h2><p>Selecting a saved record fills its fields. You can still edit them or enter details manually.</p></div></div><div className="form-grid two-col"><SelectField label="Saved student profile" value={studentRecordId} onChange={loadStudentRecord} options={students.map((item) => ({ value: String(item.id), label: `${item.student_name} · ${item.student_id} · ${item.branch}` }))} placeholder={students.length ? "Choose a saved student" : "No saved students yet"} /><SelectField label="Saved job" value={jobRecordId} onChange={loadJobRecord} options={jobs.map((item) => ({ value: String(item.id), label: `${item.job_title} · ${item.company_name}` }))} placeholder={jobs.length ? "Choose a saved job" : "No saved jobs yet"} /></div></section>
        <section className="panel form-panel"><div className="form-section-title"><div className="section-index">01</div><div><span className="panel-kicker">STUDENT PROFILE</span><h2>Candidate signals</h2><p>These map to the student columns and ML features in your CSV.</p></div><UserRound className="section-watermark" size={22} /></div>
          <div className="form-grid two-col"><TextField label="Student ID" hint="Optional · generated for this analysis if blank" value={form.student_id} onChange={(v) => update("student_id", v)} /><TextField label="Student name" value={form.student_name} onChange={(v) => update("student_name", v)} placeholder="Candidate name" /><TextField label="Email" type="email" value={form.email} onChange={(v) => update("email", v)} placeholder="name@example.com" /><SelectField label="Branch" required value={form.branch} onChange={(v) => update("branch", v)} options={dataset?.branches || ["CSE", "ECE", "EEE", "IT"]} placeholder="Choose branch" /></div>
          <div className="form-grid three-col">{featureFields.map(([key, label, hint, min, max, step]) => <NumberField key={key} label={label} hint={hint} min={min} max={max} step={step} value={form[key]} onChange={(v) => update(key, v)} required />)}</div>
          <TextField label="Student skills" hint="Comma-separated · used for job-skill matching" value={form.student_skills} onChange={(v) => update("student_skills", v)} placeholder="Python, SQL, data visualization" required />
          <div className="suggestion-row"><button className="quiet-button" type="button" disabled={busy === "suggest"} onClick={findSuggestion}>{busy === "suggest" ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />} Find a similar dataset profile</button><span>Suggestions come from an anonymized row and need your review.</span></div>
          {suggestion && <div className="suggestion-card"><div className="suggestion-icon"><Sparkles size={16} /></div><div className="suggestion-copy"><strong>Similar profile · {suggestion.similarity_pct}% signal similarity</strong><p>{suggestion.source}</p><small>{Object.keys(suggestion.suggested_fields).length} available fields can be suggested.</small></div><button type="button" className="outline-button" onClick={applySuggestion}>Fill empty fields</button></div>}
        </section>

        <section className="panel form-panel"><div className="form-section-title"><div className="section-index indigo">02</div><div><span className="panel-kicker">JOB REQUIREMENT</span><h2>Role signals</h2><p>Choose a role and add job requirements to compare the profile.</p></div><BriefcaseBusiness className="section-watermark" size={22} /></div>
          <div className="form-grid two-col"><TextField label="Job title" value={form.job_title} onChange={(v) => update("job_title", v)} placeholder="e.g. Data Analyst" list="job-titles" /><datalist id="job-titles">{jobTitleOptions.map((x) => <option key={x} value={x} />)}</datalist><TextField label="Company name" value={form.company_name} onChange={(v) => update("company_name", v)} placeholder="Company or organization" /><TextField label="Job ID" hint="Optional · dataset reference" value={form.job_id} onChange={(v) => update("job_id", v)} /><SelectField label="Role category" required value={form.role_category} onChange={(v) => update("role_category", v)} options={dataset?.role_categories || ["Business Analyst", "Data Analyst", "Data Engineer", "Data Scientist", "Machine Learning Engineer", "Python Developer"]} placeholder="Choose role" /><SelectField label="Work mode" required value={form.work_mode} onChange={(v) => update("work_mode", v)} options={dataset?.work_modes || ["Hybrid", "On-site", "Remote"]} placeholder="Choose mode" /><TextField label="Location" value={form.location} onChange={(v) => update("location", v)} placeholder="City or locations" list="locations" /><datalist id="locations">{locationOptions.map((x) => <option key={x} value={x} />)}</datalist><SelectField label="Fresher friendly" value={form.is_fresher_friendly} onChange={(v) => update("is_fresher_friendly", v)} options={[{ value: "true", label: "Yes" }, { value: "false", label: "No" }]} placeholder="Select" /><NumberField label="Minimum experience (years)" min={0} max={60} step={0.5} value={form.experience_min_yrs} onChange={(v) => update("experience_min_yrs", v)} /><NumberField label="Maximum experience (years)" min={0} max={60} step={0.5} value={form.experience_max_yrs} onChange={(v) => update("experience_max_yrs", v)} /><TextField label="Job URL" value={form.job_url} onChange={(v) => update("job_url", v)} placeholder="https://…" /></div>
          <div className="eligibility-chip"><span className={`eligibility-dot ${experienceEligible === true ? "good" : experienceEligible === false ? "bad" : ""}`} />{experienceEligible == null ? "Set the job fresher-friendly flag to show the dataset eligibility value." : experienceEligible ? "Dataset eligibility flag: eligible (same as fresher-friendly)." : "Dataset eligibility flag: not eligible (same as fresher-friendly)."}</div>
          <label className="field-label job-desc-label">Paste job description <span>OPTIONAL · dataset vocabulary matching</span></label><textarea className="textarea" rows="4" value={form.job_description} onChange={(e) => update("job_description", e.target.value)} placeholder="Paste the role description. We’ll find literal skill phrases present in your dataset vocabulary; review the extracted list." />
          <div className="extract-row"><button type="button" className="quiet-button" disabled={busy === "extract" || !form.job_description.trim()} onClick={extractFromDescription}>{busy === "extract" ? <LoaderCircle className="spin" size={15} /> : <FileText size={15} />} Find skills in description</button>{extraction && <span>{extraction.extracted_skills.length} terms found · review before matching</span>}</div>
          <TextField label="Required skills" hint="Required · comma-separated · edit extracted terms as needed" value={form.required_skills} onChange={(v) => update("required_skills", v)} placeholder="SQL, Python, communication" required />
        </section>
        <div className="form-submit-row"><span><CircleHelp size={15} /> Derived match fields are calculated from your two skill lists.</span><button className="primary-action" type="submit" disabled={busy === "analysis"}>{busy === "analysis" ? <><LoaderCircle size={16} className="spin" /> Analyzing…</> : <><Target size={16} /> Analyze this match <ArrowRight size={16} /></>}</button></div>
      </form>

      <aside className="result-column">
        {alert && <div className="result-alert"><X size={16} /><span>{alert}</span></div>}
        {success && <div className="result-success"><Check size={16} /><span>{success}</span></div>}
        <section className="panel result-card"><div className="panel-heading"><div><span className="panel-kicker">MATCH OUTPUT</span><h3>Skill gap map</h3><p>Computed from exact skill phrases.</p></div><span className="result-state">{skillResult ? "UPDATED" : "AWAITING INPUT"}</span></div>
          {skillResult ? <><div className="match-score"><div className="score-ring" style={{ "--score": `${(skillResult.match_percentage || 0) * 3.6}deg` }}><div><strong>{skillResult.match_percentage == null ? "N/A" : `${skillResult.match_percentage}%`}</strong><small>skill fit</small></div></div><div className="match-score-copy"><strong>{skillResult.matched_skills.length} of {skillResult.required_skills.length} required skills</strong><p>{skillResult.match_percentage == null ? "No required skills were recognized" : skillResult.missing_skills.length ? `${skillResult.missing_skills.length} skill gaps to explore` : "All listed skills matched"}</p></div></div><SkillList title="Matched" values={skillResult.matched_skills} tone="match" /><SkillList title="Skill gaps" values={skillResult.missing_skills} tone="gap" /><SkillList title="Additional skills" values={skillResult.additional_skills || []} tone="match" /><div className="result-footnote">{skillResult.notice}</div></> : <div className="placeholder-result"><div className="placeholder-visual"><div className="placeholder-ring ring-a" /><div className="placeholder-ring ring-b" /><span><Target size={25} /></span></div><strong>Your skill map starts here</strong><p>Enter student skills and job requirements, then run the analysis.</p></div>}
        </section>

        <section className="panel prediction-card"><div className="panel-heading"><div><span className="panel-kicker">MODEL SIGNAL</span><h3>Synthetic suitability label</h3><p>Distinct from the skill-match percentage.</p></div><span className={`tiny-status ${health?.model?.ready ? "ok" : "off"}`} /></div><SelectField label="Algorithm" value={form.algorithm} onChange={(v) => update("algorithm", v)} options={modelInfo?.available_algorithms || []} placeholder={modelInfo?.available_algorithms?.length ? "Select loaded algorithm" : "No exported algorithms available"} disabled={!health?.model?.ready} />{prediction ? <div className="prediction-output"><div className={`prediction-badge ${Number(prediction.predicted_label) === 1 ? "positive" : "negative"}`}>{Number(prediction.predicted_label) === 1 ? "Synthetic suitable (1)" : "Synthetic unsuitable (0)"}</div><p>{prediction.interpretation}</p>{prediction.class_probabilities && <div className="probability-list">{Object.entries(prediction.class_probabilities).map(([label, pct]) => <div key={label}><span>Model score for class {label}</span><strong>{(pct * 100).toFixed(1)}%</strong><div className="prob-track"><i style={{ width: `${pct * 100}%` }} /></div></div>)}</div>}{prediction.decision_score != null && <div className="derived-list"><div><span>SVM decision score (not a probability)</span><strong>{prediction.decision_score.toFixed(4)}</strong></div></div>}<small>{prediction.notice}</small></div> : <div className="model-pending"><div className="model-pending-icon"><Network size={17} /></div><p>{health?.model?.ready ? "Complete the profile and submit to see the model signal." : "Matching Colab model artifacts and verified category encoding are required before prediction."}</p></div>}<div className="synthetic-disclaimer"><CircleHelp size={14} /><span>Synthetic target · not a hiring outcome or placement guarantee.</span></div></section>

        <section className="panel derived-card"><div className="panel-heading"><div><span className="panel-kicker">AUTO-CALCULATED</span><h3>Dataset fields we derive</h3></div><span className="auto-tag"><Sparkles size={12} /> AUTO</span></div><div className="derived-list"><div><span>Matched skill count</span><strong>{skillResult?.matched_skills.length ?? "—"}</strong></div><div><span>Missing skill count</span><strong>{skillResult?.missing_skills.length ?? "—"}</strong></div><div><span>Skill match percentage</span><strong>{skillResult ? `${skillResult.match_percentage}%` : "—"}</strong></div><div><span>Experience eligible (dataset flag)</span><strong>{experienceEligible == null ? "—" : experienceEligible ? "Yes" : "No"}</strong></div><div><span>Synthetic label</span><strong>{prediction?.predicted_label ?? "—"}</strong></div></div><p className="derived-hint">IDs can be omitted. The app never asks you to type computed match counts or the model target.</p></section>
      </aside>
    </div>
  </>;
}

function TextField({ label, hint, value, onChange, placeholder = "", list, required = false, type = "text" }) {
  return <label className="field-label">{label}{required && <span className="required-mark">*</span>}{hint && <small>{hint}</small>}<input className="input" type={type} value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} list={list} required={required} /></label>;
}
function NumberField({ label, hint, value, onChange, min, max, step = 1, required = false }) {
  return <label className="field-label">{label}{required && <span className="required-mark">*</span>}{hint && <small>{hint}</small>}<input className="input" type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value)} min={min} max={max} step={step} required={required} /></label>;
}
function SelectField({ label, hint, value, onChange, options, placeholder, required = false, disabled = false }) {
  return <label className="field-label">{label}{required && <span className="required-mark">*</span>}{hint && <small>{hint}</small>}<select className="input select-input" value={value ?? ""} onChange={(e) => onChange(e.target.value)} required={required} disabled={disabled}><option value="">{placeholder || "Select an option"}</option>{options.map((option) => { const val = typeof option === "string" ? option : option.value; const text = typeof option === "string" ? option : option.label; return <option value={val} key={val}>{text}</option>; })}</select></label>;
}
function SkillList({ title, values, tone }) {
  return <div className={`skill-list ${tone}`}><div className="skill-list-head"><strong>{title}</strong><span>{values.length}</span></div>{values.length ? <div className="skill-chips">{values.map((value) => <span key={value}>{tone === "match" ? <Check size={11} /> : <ArrowDownRight size={11} />}{value}</span>)}</div> : <p className="no-skills">{tone === "match" ? "No exact matches yet." : "No skill gaps found."}</p>}</div>;
}

function ModelRoom({ modelInfo, performance, health }) {
  const metrics = performance?.evaluation_metrics || modelInfo?.evaluation_metrics || [];
  const ordered = [...metrics].sort((a, b) => b.suitable_f1_pct - a.suitable_f1_pct);
  const selectedModel = performance?.selected_model || modelInfo?.selected_model;
  const selectedMetric = ordered.find((metric) => metric.model === selectedModel);
  return <>
    <PageHeading eyebrow="MODEL TRANSPARENCY" title={<>Understand the<br className="desktop-break" /> <span className="gradient-text">signal behind the score.</span></>} description="Notebook evaluation metrics shown with the limitations needed to interpret them responsibly." action={<div className={`model-readiness ${health?.model?.ready ? "ready" : "not-ready"}`}><span />{health?.model?.ready ? "Prediction ready" : "Export or encoding check required"}</div>} />
    <div className="model-summary-grid"><div className="model-summary panel"><span className="panel-kicker">CONFIGURED COLAB MODEL</span><h2>{modelInfo?.model_type || "Random Forest Classifier"}</h2><p>Target column: <code>{modelInfo?.target_column || "suitability_label_synthetic"}</code></p><div className="feature-pills">{(modelInfo?.features || []).slice(0, 6).map((feature) => <span key={feature}>{feature.replaceAll("_", " ")}</span>)}{(modelInfo?.features || []).length > 6 && <span>+{modelInfo.features.length - 6} more inputs</span>}</div></div><div className="best-model-card"><span className="best-model-icon"><Sparkles size={17} /></span><span className="panel-kicker">SELECTED BY TRAINING-ONLY CV</span><strong>{selectedModel || "Unavailable"}</strong><p>{selectedModel ? `Chosen using grouped training validation.${selectedMetric ? ` Held-out suitable-class F1: ${selectedMetric.suitable_f1_pct.toFixed(2)}%.` : ""}` : "No verified model selection is recorded."}</p></div></div>
    <section className="panel model-table-panel"><div className="panel-heading"><div><span className="panel-kicker">GROUPED TEST SPLIT · {performance?.evaluation_rows ?? modelInfo?.evaluation_rows ?? "Unavailable"} ROWS</span><h3>Evaluation comparison</h3><p>Notebook test metrics; the test split is not used to select the model.</p></div><span className="metric-badge">{(performance?.historical ?? modelInfo?.historical) ? "Historical notebook output" : "Latest notebook training run"}</span></div>{ordered.length ? <><div className="model-chart"><Suspense fallback={<div className="page-loading">Loading model chart…</div>}><ModelF1Chart data={ordered}/></Suspense></div><div className="table-scroll"><table className="metrics-table"><thead><tr><th>MODEL</th><th>ACCURACY</th><th>SUITABLE PRECISION</th><th>SUITABLE RECALL</th><th>SUITABLE F1</th></tr></thead><tbody>{ordered.map((m, index) => <tr key={m.model}><td><span className={`rank-dot ${m.model === selectedModel ? "top" : ""}`}>{String(index + 1).padStart(2, "0")}</span><strong>{m.model}</strong></td><td>{m.accuracy_pct.toFixed(2)}%</td><td>{m.suitable_precision_pct.toFixed(2)}%</td><td>{m.suitable_recall_pct.toFixed(2)}%</td><td><strong className="f1-cell">{m.suitable_f1_pct.toFixed(2)}%</strong></td></tr>)}</tbody></table></div></> : <EmptyPanel text="Evaluation metrics are not available." />}</section>
    <section className="confusion-section"><div className="section-bar"><div><h2>Historical confusion matrices</h2><p>Rows are true labels; columns are predicted labels.</p></div><span className="metric-badge">Notebook output</span></div><div className="confusion-grid">{Object.entries(performance?.confusion_matrices || {}).map(([name, matrix]) => <ConfusionMatrix key={name} name={name} matrix={matrix} />)}</div></section>
    {performance?.unsupervised && <section className="unsupervised-grid"><article className="panel unsup-card"><span className="panel-kicker">HISTORICAL UNSUPERVISED ANALYSIS</span><h3>K-Means · {performance.unsupervised.kmeans_clusters} clusters</h3><p>Training cluster counts reported by the notebook; clustering artifacts are not exported for live inference.</p><div className="cluster-bars">{performance.unsupervised.kmeans_training_cluster_counts.map((count, i) => <div key={i}><span>Cluster {i}</span><div><i style={{ width: `${count / Math.max(...performance.unsupervised.kmeans_training_cluster_counts) * 100}%` }} /></div><strong>{count.toLocaleString()}</strong></div>)}</div></article><article className="panel unsup-card"><span className="panel-kicker">PCA SUMMARY</span><h3>Dimension reduction</h3><p>Historical notebook output from the scaled training matrix.</p><div className="pca-stats"><div><strong>{performance.unsupervised.pca_two_component_variance_pct}%</strong><span>variance in 2 components</span></div><div><strong>{performance.unsupervised.pca_components_for_80_pct_variance}</strong><span>components for at least 80%</span></div><div><strong>{performance.unsupervised.pca_cumulative_variance_at_14_components_pct}%</strong><span>reported at 14 components</span></div></div></article></section>}
    {Object.keys(performance?.feature_importance || {}).length > 0 && <section className="panel importance-panel"><span className="panel-kicker">LOADED TREE ARTIFACTS</span><h3>Feature importance</h3>{Object.entries(performance.feature_importance).map(([name, features]) => <div key={name} className="importance-block"><strong>{name}</strong>{features.slice(0, 8).map((item) => <div className="gap-row" key={item.feature}><span>{item.feature}</span><div><i style={{ width: `${item.importance * 100}%` }} /></div><strong>{(item.importance * 100).toFixed(1)}%</strong></div>)}</div>)}</section>}
    <div className="model-caveats"><div className="caveat-icon"><CircleHelp size={17} /></div><div><strong>Read these results with care</strong><p>The dataset target is synthetic, the classes are imbalanced, and even the top suitable-class F1 is modest. These figures describe the notebook experiment—not real placement success and not a promise about an individual student.</p></div></div>
    <section className="panel artifact-panel"><div className="artifact-status"><div className="artifact-lamp"><Activity size={18} /></div><div><span className="panel-kicker">RUNTIME ARTIFACT STATUS</span><h3>{health?.model?.ready ? "Model bundle loaded" : "Prediction is disabled"}</h3><p>{health?.model?.errors?.length ? health.model.errors.join("; ") : "The artifact bundle is loaded and category encoding has been verified."}</p></div></div><div className="artifact-list"><span><i className={health?.model?.available_algorithms?.includes("Random Forest") ? "done" : "missing"} />Random Forest estimator</span><span><i className={health?.model?.medians_ready ? "done" : "missing"} />Training medians</span><span><i className={health?.model?.scaler_ready ? "done" : "missing"} />Fitted scaler</span><span><i className={health?.model?.category_encoding_verified ? "done" : "missing"} />Category encoding verified</span></div></section>
  </>;
}

function ConfusionMatrix({ name, matrix }) {
  const max = Math.max(1, ...matrix.flat());
  const cells = [
    ["True unsuitable · predicted unsuitable", matrix[0][0]],
    ["True unsuitable · predicted suitable", matrix[0][1]],
    ["True suitable · predicted unsuitable", matrix[1][0]],
    ["True suitable · predicted suitable", matrix[1][1]],
  ];
  return <article className="panel confusion-card"><div className="confusion-title"><strong>{name}</strong><span>TRUE ↓ · PREDICTED →</span></div><div className="matrix-grid">{cells.map(([label, value]) => <div key={label} className="matrix-cell" title={label} style={{ "--cell-alpha": 0.08 + value / max * 0.55 }}><small>{label.replace("True ", "").replace(" · predicted ", " → ")}</small><strong>{value.toLocaleString()}</strong></div>)}</div><div className="matrix-axes"><span>Rows: actual</span><span>Columns: predicted</span></div></article>;
}

export default App;
