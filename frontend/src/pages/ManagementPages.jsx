import React, { useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, BriefcaseBusiness, Check, Download, ExternalLink, FileText, LoaderCircle, Plus, Search, Sparkles, Trash2, UserRound, X } from "lucide-react";
import { Link } from "react-router-dom";
import "./ResourceManagement.css";
import {
  createJob, createReport, createStudent, deleteAnalysis, deleteJob, deleteStudent,
  createCareerResource, errorMessage, exportHistoryCsv, getCareerResources, getHistory, getJobs, getRecommendations, getStudents,
  updateJob, updateRecommendation, updateStudent,
} from "../services/api.js";

const numberFields = [
  ["cgpa", "CGPA", 0, 10, 0.01], ["coding_skill_score", "Coding score", 0, 100, 1],
  ["aptitude_score", "Aptitude score", 0, 100, 1], ["communication_skill_score", "Communication", 0, 100, 1],
  ["logical_reasoning_score", "Logical reasoning", 0, 100, 1], ["mock_interview_score", "Mock interview", 0, 100, 1],
  ["backlogs", "Backlogs", 0, 100, 1], ["github_repos", "GitHub repositories", 0, 100000, 1],
  ["internships_count", "Internships", 0, 100, 1], ["projects_count", "Projects", 0, 1000, 1],
];
const modeOptions = ["Hybrid", "On-site", "Remote"];
const branchOptions = ["CSE", "ECE", "EEE", "IT"];

function Heading({ eyebrow, title, text, action }) {
  return <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-mark" />{eyebrow}</div><h1>{title}</h1><p>{text}</p></div>{action}</div>;
}
function Input({ label, value, onChange, type = "text", min, max, step, required, placeholder, hint, options }) {
  const common = { className: "input", value: value ?? "", required, onChange: (e) => onChange(e.target.value) };
  return <label className="field-label">{label}{required && <span className="required-mark">*</span>}{hint && <small>{hint}</small>}{options ? <select {...common}><option value="">Choose…</option>{options.map((o) => <option key={o} value={o}>{o}</option>)}</select> : <input {...common} type={type} min={min} max={max} step={step} placeholder={placeholder} />}</label>;
}
function Notice({ error, success }) { return <>{error && <div className="result-alert"><X size={15} />{error}</div>}{success && <div className="result-success"><Check size={15} />{success}</div>}</>; }

export function LandingPage() {
  return <><Heading eyebrow="PLACEMENT INTELLIGENCE" title={<>Intelligent job matching,<br /><span className="gradient-text">with evidence.</span></>} text="A research prototype for candidate suitability, job-description skill matching, and transparent skill-gap analysis." action={<Link className="primary-action" to="/">Open dashboard <ArrowRight size={15} /></Link>} /><section className="hero-strip landing-hero"><div className="hero-copy"><div className="hero-kicker"><span className="pulse-ring" /> RESEARCH · DATA-AWARE · EXPLAINABLE</div><h2>Skills show the path.<br /><em>Evidence guides it.</em></h2><p>Manage student and job records, inspect skill overlap, and compare the notebook’s historical model evaluation.</p><Link className="hero-link" to="/analysis">Start an analysis <ArrowRight size={15} /></Link></div><div className="hero-art" aria-hidden="true"><div className="orb orb-back" /><div className="orb orb-front"><div className="orb-core"><Sparkles size={28} /></div><span className="orbit orbit-one" /><span className="orbit orbit-two" /><span className="orbit-dot dot-one" /><span className="orbit-dot dot-two" /><span className="orbit-dot dot-three" /></div></div><div className="hero-foot"><span>01 <i /> PROFILE</span><span>02 <i /> ROLE</span><span>03 <i /> INSIGHT</span></div></section><div className="section-bar"><div><h2>How it works</h2><p>Three steps, each grounded in an explicit data source.</p></div></div><section className="landing-steps">{[["01", "Build a profile", "Store candidate details and student skills in the local SQLite database."], ["02", "Add a job", "Save a description or enter required skills; literal terms are checked against the supplied dataset vocabulary."], ["03", "Review the match", "See exact skill overlap, missing skills, learning activities, and historical model metrics."]].map(([n, title, text]) => <article className="panel landing-step" key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}</section><div className="model-caveats"><div className="caveat-icon"><FileText size={16} /></div><div><strong>Model limitation</strong><p>The notebook target is synthetic. Inference uses the saved bundle only when its matching preprocessing files and scikit-learn runtime are ready.</p></div></div></>;
}

export function StudentsPage() {
  const blank = Object.fromEntries([...numberFields.map(([k]) => [k, ""]), ...["student_id","student_name","email","branch","student_skills","degree","specialization","graduation_year","experience_years","areas_of_interest","preferred_job_roles","certifications","projects"].map(k=>[k,""])]);
  const [form, setForm] = useState(blank), [items, setItems] = useState([]), [selected, setSelected] = useState(null);
  const [editing, setEditing] = useState(null), [q, setQ] = useState(""), [branch, setBranch] = useState(""), [error, setError] = useState(""), [success, setSuccess] = useState(""), [busy, setBusy] = useState(false);
  async function load() { try { const data = await getStudents({ q, branch, limit: 200 }); setItems(data.items); setError(""); } catch (e) { setError(errorMessage(e)); } }
  useEffect(() => { load(); }, []);
  const set = (k, v) => setForm((old) => ({ ...old, [k]: v }));
  function edit(item) { setEditing(item.id); setForm(Object.fromEntries(Object.keys(blank).map((k) => [k, item[k] ?? ""]))); window.scrollTo({ top: 0, behavior: "smooth" }); }
  async function submit(e) { e.preventDefault(); setBusy(true); setError(""); setSuccess(""); const payload = { ...form }; for (const [key] of numberFields) payload[key] = Number(payload[key]); for(const key of ["graduation_year","experience_years"]) payload[key]=payload[key]?Number(payload[key]):null; try { if (editing) await updateStudent(editing, payload); else await createStudent(payload); setForm(blank); setEditing(null); setSuccess(editing ? "Student profile updated." : "Student profile saved to SQLite."); await load(); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); } }
  async function remove(item) { if (!window.confirm(`Delete profile for ${item.student_name}?`)) return; try { await deleteStudent(item.id); setSuccess("Student profile deleted."); if (selected?.id === item.id) setSelected(null); await load(); } catch (e) { setError(errorMessage(e)); } }
  return <><Heading eyebrow="STUDENT DIRECTORY" title={<>Student <span className="gradient-text">management.</span></>} text="Create, search, edit, and remove student profiles stored in SQLite." action={<span className="metric-badge">{items.length} shown</span>} /><Notice error={error} success={success} /><div className="management-layout"><form className="panel management-form" onSubmit={submit}><div className="form-section-title"><div className="section-index"><UserRound size={14} /></div><div><span className="panel-kicker">PROFILE RECORD</span><h2>{editing ? "Edit student" : "Add student"}</h2><p>Fields are validated by the backend.</p></div></div><div className="form-grid two-col"><Input label="Student ID" required value={form.student_id} onChange={(v) => set("student_id", v)} /><Input label="Student name" required value={form.student_name} onChange={(v) => set("student_name", v)} /><Input label="Email" type="email" value={form.email} onChange={(v) => set("email", v)} /><Input label="Branch" required options={branchOptions} value={form.branch} onChange={(v) => set("branch", v)} /></div><div className="form-grid two-col">{numberFields.map(([k, label, min, max, step]) => <Input key={k} label={label} type="number" min={min} max={max} step={step} required value={form[k]} onChange={(v) => set(k, v)} />)}</div><Input label="Student skills" hint="Comma-separated exact phrases" value={form.student_skills} onChange={(v) => set("student_skills", v)} placeholder="Python, SQL, teamwork" /><Input label="Degree" value={form.degree} onChange={v=>set("degree",v)} placeholder="B.Tech"/><Input label="Specialization" value={form.specialization} onChange={v=>set("specialization",v)}/><div className="form-grid two-col"><Input label="Graduation year" type="number" min={2000} max={2100} value={form.graduation_year} onChange={v=>set("graduation_year",v)}/><Input label="Experience years" type="number" min={0} max={60} step={0.1} value={form.experience_years} onChange={v=>set("experience_years",v)}/></div><Input label="Areas of interest" value={form.areas_of_interest} onChange={v=>set("areas_of_interest",v)}/><Input label="Preferred job roles" value={form.preferred_job_roles} onChange={v=>set("preferred_job_roles",v)}/><label className="field-label">Projects<textarea className="textarea" rows="2" value={form.projects} onChange={e=>set("projects",e.target.value)} placeholder="One project per line"/></label><label className="field-label">Certifications<textarea className="textarea" rows="2" value={form.certifications} onChange={e=>set("certifications",e.target.value)} placeholder="One certification per line"/></label><div className="button-row"><button className="primary-action" disabled={busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />}{editing ? "Save changes" : "Add profile"}</button>{editing && <button className="outline-button" type="button" onClick={() => { setForm(blank); setEditing(null); }}>Cancel edit</button>}</div></form><section className="panel data-table-panel"><div className="panel-heading"><div><span className="panel-kicker">MANAGED STUDENTS</span><h3>Profiles</h3><p>Records are persisted locally in SQLite.</p></div></div><div className="filter-bar"><label className="search-box"><Search size={15} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name, ID, or email" onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), load())} /></label><select className="input filter-select" value={branch} onChange={(e) => setBranch(e.target.value)}><option value="">All branches</option>{branchOptions.map((x) => <option key={x}>{x}</option>)}</select><button className="quiet-button" onClick={load}>Search</button></div><div className="table-scroll"><table className="metrics-table records-table"><thead><tr><th>STUDENT</th><th>BRANCH</th><th>CGPA</th><th>SKILLS</th><th>ACTIONS</th></tr></thead><tbody>{items.map((item) => <tr key={item.id} onClick={() => setSelected(item)}><td><strong>{item.student_name}</strong><small>{item.student_id}</small></td><td>{item.branch}</td><td>{Number(item.cgpa).toFixed(2)}</td><td>{item.student_skills || "—"}</td><td><div className="row-actions"><button type="button" className="text-link" onClick={(e) => { e.stopPropagation(); edit(item); }}>Edit</button><button type="button" className="danger-icon" onClick={(e) => { e.stopPropagation(); remove(item); }} aria-label="Delete student"><Trash2 size={14} /></button></div></td></tr>)}</tbody></table>{!items.length && <div className="empty-panel"><span><UserRound size={18} /></span><p>No managed profiles yet. Add a student to begin.</p></div>}</div>{selected &&   <div className="detail-strip"><div><span className="panel-kicker">PROFILE DETAILS</span><strong>{selected.student_name} · {selected.student_id}</strong><p>{selected.email || "No email"} · {selected.branch} · {selected.internships_count} internships · {selected.projects_count} projects</p></div><Link className="text-link" to={`/career?student_id=${selected.id}`}>Open student intelligence <ArrowRight size={14}/></Link><button className="icon-btn" onClick={() => setSelected(null)}><X size={16} /></button></div>}</section></div></>;
}

export function JobsPage() {
  const blank = { external_job_id: "", company_name: "", job_title: "", job_description: "", required_skills: "", optional_skills: "", experience_min_yrs: "", experience_max_yrs: "", is_fresher_friendly: "", location: "", work_mode: "", role_category: "", job_url: "", min_cgpa: "", eligible_branches: "", required_certifications: "", required_degree: "" };
  const [form, setForm] = useState(blank), [items, setItems] = useState([]), [editing, setEditing] = useState(null), [q, setQ] = useState(""), [error, setError] = useState(""), [success, setSuccess] = useState(""), [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((old) => ({ ...old, [k]: v }));
  async function load() { try { setItems((await getJobs({ q, limit: 200 })).items); setError(""); } catch (e) { setError(errorMessage(e)); } }
  useEffect(() => { load(); }, []);
  async function submit(e) { e.preventDefault(); setBusy(true); setError(""); try { const payload = { ...form, min_cgpa: form.min_cgpa || null, experience_min_yrs: form.experience_min_yrs || null, experience_max_yrs: form.experience_max_yrs || null, is_fresher_friendly: form.is_fresher_friendly === "" ? null : form.is_fresher_friendly === "true" }; if (editing) await updateJob(editing, payload); else await createJob(payload); setSuccess(editing ? "Job listing updated." : "Job description stored in SQLite."); setForm(blank); setEditing(null); await load(); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); } }
  async function remove(item) { if (!window.confirm(`Delete ${item.job_title} at ${item.company_name}?`)) return; try { await deleteJob(item.id); setSuccess("Job listing deleted."); await load(); } catch (e) { setError(errorMessage(e)); } }
  return <><Heading eyebrow="ROLE LIBRARY" title={<>Job <span className="gradient-text">management.</span></>} text="Maintain job descriptions, extracted requirements, and role metadata." action={<span className="metric-badge">{items.length} jobs shown</span>} /><Notice error={error} success={success} /><div className="management-layout"><form className="panel management-form" onSubmit={submit}><div className="form-section-title"><div className="section-index indigo"><BriefcaseBusiness size={14} /></div><div><span className="panel-kicker">JOB RECORD</span><h2>{editing ? "Edit job" : "Add job description"}</h2><p>Extracted skills are suggestions to review.</p></div></div><div className="form-grid two-col"><Input label="Company" required value={form.company_name} onChange={(v) => set("company_name", v)} /><Input label="Job title" required value={form.job_title} onChange={(v) => set("job_title", v)} /><Input label="Job category / role" value={form.role_category} onChange={(v) => set("role_category", v)} placeholder="Any role name, including a custom role" /><Input label="Work mode" options={modeOptions} value={form.work_mode} onChange={(v) => set("work_mode", v)} /><Input label="Location" value={form.location} onChange={(v) => set("location", v)} /><Input label="External job ID" value={form.external_job_id} onChange={(v) => set("external_job_id", v)} /><Input label="Minimum CGPA eligibility" type="number" min={0} max={10} step={0.1} value={form.min_cgpa} onChange={v=>set("min_cgpa",v)}/><Input label="Eligible branches" value={form.eligible_branches} onChange={v=>set("eligible_branches",v)} placeholder="CSE, IT (leave blank for any)"/><Input label="Required certifications" value={form.required_certifications} onChange={v=>set("required_certifications",v)} placeholder="Comma-separated exact names"/><Input label="Required degree (optional)" value={form.required_degree} onChange={v=>set("required_degree",v)} placeholder="e.g. B.Tech"/><Input label="Min experience (years)" type="number" min={0} max={60} step={0.5} value={form.experience_min_yrs} onChange={(v) => set("experience_min_yrs", v)} /><Input label="Max experience (years)" type="number" min={0} max={60} step={0.5} value={form.experience_max_yrs} onChange={(v) => set("experience_max_yrs", v)} /><Input label="Fresher friendly" options={["Yes", "No"]} value={form.is_fresher_friendly === "true" ? "Yes" : form.is_fresher_friendly === "false" ? "No" : ""} onChange={(v) => set("is_fresher_friendly", v === "Yes" ? "true" : v === "No" ? "false" : "")} /><Input label="Job URL" value={form.job_url} onChange={(v) => set("job_url", v)} placeholder="https://…" /></div><label className="field-label">Job description<textarea className="textarea" rows="5" value={form.job_description} onChange={(e) => set("job_description", e.target.value)} placeholder="Paste the full role description…" /></label><label className="field-label">Required skills<small>Comma-separated. If empty, literal matches are extracted from the description vocabulary.</small><textarea className="textarea" rows="3" value={form.required_skills} onChange={(e) => set("required_skills", e.target.value)} placeholder="Python, SQL, communication" /></label><label className="field-label">Optional skills<small>Optional preferred skills are compared and recommended separately.</small><textarea className="textarea" rows="2" value={form.optional_skills} onChange={(e) => set("optional_skills", e.target.value)} placeholder="Docker, Tableau" /></label><div className="button-row"><button className="primary-action" disabled={busy}>{busy ? <LoaderCircle className="spin" size={15} /> : <Plus size={15} />}{editing ? "Save changes" : "Save job"}</button>{editing && <button className="outline-button" type="button" onClick={() => { setForm(blank); setEditing(null); }}>Cancel</button>}</div></form><section className="panel data-table-panel"><div className="panel-heading"><div><span className="panel-kicker">SAVED JOBS</span><h3>Job descriptions</h3><p>Search stored roles and review extracted requirements.</p></div></div><div className="filter-bar"><label className="search-box"><Search size={15} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, company, skills" onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), load())} /></label><button className="quiet-button" onClick={load}>Search</button></div><div className="job-record-list">{items.map((item) => <article className="job-record" key={item.id}><div className="job-record-icon"><BriefcaseBusiness size={17} /></div><div className="job-record-copy"><strong>{item.job_title}</strong><span>{item.company_name} · {item.role_category || "Uncategorized"} · {item.work_mode || "Mode not set"}</span><small>Required: {item.required_skills || "—"} · Optional: {item.optional_skills || "—"}</small></div><div className="row-actions"><button className="text-link" onClick={() => { setEditing(item.id); setForm(Object.fromEntries(Object.keys(blank).map((key) => [key, item[key] == null ? "" : String(item[key])]))); window.scrollTo({ top: 0, behavior: "smooth" }); }}>Edit</button><button className="danger-icon" onClick={() => remove(item)} aria-label="Delete job"><Trash2 size={14} /></button></div></article>)}{!items.length && <div className="empty-panel"><span><BriefcaseBusiness size={18} /></span><p>No saved jobs yet. Add a job description to start matching.</p></div>}</div></section></div></>;
}

export function ResourceCatalogPage() {
  const blank = {
    title: "", skill: "", domain: "", provider: "", resource_type: "",
    difficulty: "", url: "", description: "", relevant_roles: "", url_verified: false,
  };
  const [form, setForm] = useState(blank);
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  async function load() {
    try {
      setItems((await getCareerResources(q ? { q } : {})).items);
      setError("");
    } catch (e) { setError(errorMessage(e)); }
  }
  useEffect(() => { load(); }, []);
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setSuccess("");
    try {
      await createCareerResource(form);
      setForm(blank);
      setSuccess("Resource saved to the shared SQLite catalogue.");
      await load();
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  }
  return <>
    <Heading eyebrow="LEARNING CATALOGUE" title={<>Resource <span className="gradient-text">management.</span></>} text="Add a verified resource for any skill or custom role. Recommendations are driven by saved job requirements, not a role allowlist." action={<span className="metric-badge">{items.length} shown</span>} />
    <Notice error={error} success={success} />
    <div className="model-caveats"><div className="caveat-icon"><BookOpen size={16}/></div><div><strong>Local prototype access</strong><p>This application has no authentication or administrator authorization. Only use this management screen in a trusted local environment; it is not safe to expose publicly.</p></div></div>
    <div className="management-layout">
      <form className="panel management-form" onSubmit={submit}>
        <div className="form-section-title"><div className="section-index indigo"><BookOpen size={14}/></div><div><span className="panel-kicker">CATALOGUE ENTRY</span><h2>Add learning resource</h2><p>Only save provider pages you have opened and checked.</p></div></div>
        <Input label="Resource title" required value={form.title} onChange={(v)=>set("title",v)} />
        <div className="form-grid two-col">
          <Input label="Skill covered" required value={form.skill} onChange={(v)=>set("skill",v)} placeholder="e.g. Infrastructure as Code" />
          <Input label="Domain" required value={form.domain} onChange={(v)=>set("domain",v)} placeholder="e.g. Cloud and DevOps" />
          <Input label="Provider" required value={form.provider} onChange={(v)=>set("provider",v)} />
          <Input label="Resource type" required value={form.resource_type} onChange={(v)=>set("resource_type",v)} placeholder="Documentation, course, certification..." />
          <Input label="Difficulty" required value={form.difficulty} onChange={(v)=>set("difficulty",v)} placeholder="Beginner, intermediate, all levels" />
          <Input label="Provider URL" type="url" required value={form.url} onChange={(v)=>set("url",v)} placeholder="https://…" />
        </div>
        <label className="field-label">Description<textarea className="textarea" rows="3" required maxLength="2000" value={form.description} onChange={(e)=>set("description",e.target.value)} /></label>
        <label className="field-label">Related job roles<small>Optional, comma-separated. A resource can still match a custom role through its skill.</small><textarea className="textarea" rows="2" value={form.relevant_roles} onChange={(e)=>set("relevant_roles",e.target.value)} placeholder="Cloud Engineer, Custom Platform Role" /></label>
        <label className="field-label resource-verification"><input type="checkbox" required checked={form.url_verified} onChange={(e)=>set("url_verified",e.target.checked)} /><span>I opened this URL and confirmed it is a relevant provider page. The server records this confirmation; it does not fetch or independently verify the URL.</span></label>
        <button className="primary-action" disabled={busy}>{busy?<LoaderCircle className="spin" size={15}/>:<Plus size={15}/>}Add resource</button>
      </form>
      <section className="panel data-table-panel">
        <div className="panel-heading"><div><span className="panel-kicker">SAVED RESOURCE CATALOGUE</span><h3>Skill-linked learning</h3><p>Custom entries are persisted and available to role-independent recommendations.</p></div></div>
        <div className="filter-bar"><label className="search-box"><Search size={15}/><input value={q} onChange={(e)=>setQ(e.target.value)} placeholder="Search title, skill, domain, or provider" onKeyDown={(e)=>e.key==="Enter"&&(e.preventDefault(),load())}/></label><button className="quiet-button" type="button" onClick={load}>Search</button></div>
        <div className="job-record-list">{items.map((item)=><article className="job-record" key={item.id}><div className="job-record-icon"><BookOpen size={17}/></div><div className="job-record-copy"><strong>{item.title}</strong><span>{item.skill} · {item.domain} · {item.provider}</span><small>{item.difficulty} · {item.type} · {item.verified?"Confirmed":"Unverified"}</small></div><a className="text-link" href={item.url} target="_blank" rel="noreferrer" aria-label={`Open ${item.title}`}><ExternalLink size={14}/></a></article>)}{!items.length&&<div className="empty-panel"><span><BookOpen size={18}/></span><p>No resources match this search. Add a verified provider resource to support a new skill.</p></div>}</div>
      </section>
    </div>
  </>;
}

export function HistoryPage() {
  const [q, setQ] = useState(""), [items, setItems] = useState([]), [error, setError] = useState(""), [success, setSuccess] = useState("");
  async function load() { try { setItems((await getHistory({ q })).items); setError(""); } catch (e) { setError(errorMessage(e)); } }
  useEffect(() => { load(); }, []);
  async function remove(item) { if (!window.confirm(`Delete analysis #${item.id}?`)) return; try { await deleteAnalysis(item.id); setSuccess("Analysis history deleted."); await load(); } catch (e) { setError(errorMessage(e)); } }
  return <><Heading eyebrow="SAVED WORK" title={<>Analysis <span className="gradient-text">history.</span></>} text="The latest 500 submitted matches are shown from SQLite; use search to narrow them." /><Notice error={error} success={success} /><section className="panel data-table-panel"><div className="filter-bar"><label className="search-box"><Search size={15} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search student, role, or company" onKeyDown={(e) => e.key === "Enter" && load()} /></label><button className="quiet-button" onClick={load}>Search history</button><span className="metric-badge">{items.length} shown (max 500)</span></div><div className="table-scroll"><table className="metrics-table records-table"><thead><tr><th>STUDENT</th><th>JOB</th><th>SKILL FIT</th><th>SYNTHETIC LABEL</th><th>DATE</th><th></th></tr></thead><tbody>{items.map((a) => <tr key={a.id}><td><strong>{a.student_name || "Unregistered profile"}</strong><small>{a.student_id}</small></td><td><strong>{a.job_title || "Job analysis"}</strong><small>{a.company_name} · {a.role_category}</small></td><td>{a.skill_match_pct == null ? "—" : `${a.skill_match_pct}%`}</td><td>{a.predicted_label == null ? "Unavailable" : a.predicted_label ? "Synthetic suitable" : "Synthetic unsuitable"}</td><td>{new Date(a.created_at + (a.created_at.endsWith("Z") ? "" : "Z")).toLocaleDateString()}</td><td><button className="danger-icon" onClick={() => remove(a)} aria-label="Delete analysis"><Trash2 size={14} /></button></td></tr>)}</tbody></table>{!items.length && <div className="empty-panel"><span><FileText size={18} /></span><p>No saved analyses yet. Run an analysis to create history.</p></div>}</div></section></>;
}

export function LearningPage() {
  const [items, setItems] = useState([]), [students, setStudents] = useState([]), [jobs, setJobs] = useState([]);
  const [studentFilter, setStudentFilter] = useState(""), [jobFilter, setJobFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState(""), [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("priority"), [search, setSearch] = useState("");
  const [suppressed, setSuppressed] = useState(0), [busyId, setBusyId] = useState(null), [error, setError] = useState("");
  async function load() {
    try {
      const params = Object.fromEntries(Object.entries({
        student_record_id: studentFilter, job_record_id: jobFilter,
        role_category: roleFilter, completed: statusFilter,
      }).filter(([, value]) => value !== ""));
      const result = await getRecommendations(params);
      setItems(result.items);
      setSuppressed(result.duplicate_rows_suppressed || 0);
      setError("");
    } catch (e) { setError(errorMessage(e)); }
  }
  useEffect(() => {
    Promise.all([getStudents({ limit: 500 }), getJobs({ limit: 500 })])
      .then(([studentData, jobData]) => { setStudents(studentData.items); setJobs(jobData.items); })
      .catch((e) => setError(errorMessage(e)));
  }, []);
  useEffect(() => { load(); }, [studentFilter, jobFilter, roleFilter, statusFilter]);
  async function toggle(item) {
    setBusyId(item.id);
    try { await updateRecommendation(item.id, !Boolean(item.is_completed)); await load(); }
    catch (e) { setError(errorMessage(e)); }
    finally { setBusyId(null); }
  }
  const visibleItems = useMemo(() => {
    const query = search.trim().toLowerCase();
    return items
      .filter((item) => !query || [
        item.skill, item.job_title, item.company_name, item.role_category,
        item.resource?.title, item.resource?.provider,
      ].some((value) => String(value || "").toLowerCase().includes(query)))
      .sort((a, b) => sortBy === "skill"
        ? a.skill.localeCompare(b.skill)
        : sortBy === "role"
          ? `${a.role_category} ${a.job_title}`.localeCompare(`${b.role_category} ${b.job_title}`)
          : (b.priority_rank || 1) - (a.priority_rank || 1) || a.skill.localeCompare(b.skill));
  }, [items, search, sortBy]);
  return <><Heading eyebrow="LEARNING PATH" title={<>Skill gaps into <span className="gradient-text">practice.</span></>} text="One recommendation per student, saved role, and normalized skill. Priority reflects repeated missing requirements, not invented job weights." />
    <Notice error={error} />
    <section className="panel learning-recommendation-controls">
      <label className="search-box"><Search size={15}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search skill, role, or resource"/></label>
      <select className="input filter-select" value={studentFilter} onChange={e=>setStudentFilter(e.target.value)}><option value="">All students</option>{students.map(item=><option key={item.id} value={item.id}>{item.student_name} · {item.student_id}</option>)}</select>
      <select className="input filter-select" value={jobFilter} onChange={e=>setJobFilter(e.target.value)}><option value="">All jobs</option>{jobs.map(item=><option key={item.id} value={item.id}>{item.job_title} · {item.company_name}</option>)}</select>
      <select className="input filter-select" value={roleFilter} onChange={e=>setRoleFilter(e.target.value)}><option value="">All roles</option>{[...new Set(items.map(item=>item.role_category).filter(Boolean))].sort().map(role=><option key={role}>{role}</option>)}</select>
      <select className="input filter-select" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option value="">All statuses</option><option value="false">In progress</option><option value="true">Completed</option></select>
      <select className="input filter-select" value={sortBy} onChange={e=>setSortBy(e.target.value)}><option value="priority">Sort: priority</option><option value="skill">Sort: skill</option><option value="role">Sort: role</option></select>
    </section>
    <p className="learning-dedupe-note">{visibleItems.length} recommendations · {suppressed} duplicate historical rows are retained in SQLite and combined here.</p>
    <div className="table-scroll"><table className="metrics-table records-table learning-recommendation-table"><thead><tr><th>PRIORITY</th><th>MISSING SKILL</th><th>STUDENT / ROLE</th><th>CURATED RESOURCE</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>
      {visibleItems.map(item=><tr key={item.recommendation_key||item.id}>
        <td><strong className={item.priority==="High"?"priority-high":"priority-required"}>{item.priority||"Required"}</strong><small>{item.priority_basis}</small></td>
        <td><strong>{item.skill}</strong><small>{item.requirement_type==="optional"?"Optional requirement":"Mandatory requirement"} · {item.category||"Skill gap"}{item.duplicate_count>1?` · ${item.duplicate_count} saved records combined`:""}</small></td>
        <td><strong>{item.student_name||item.student_id||"Candidate"}</strong><small>{item.job_title||item.role_category||"Target role"} · {item.company_name||"Company not recorded"}</small></td>
        <td>{item.resource?<><a className="recommendation-resource-link" href={item.resource.url} target="_blank" rel="noreferrer">{item.resource.title}<ExternalLink size={12}/></a><small>{item.resource.provider} · {item.resource.type} · {item.resource.difficulty}</small></>:<><span>Resource missing for this skill</span><small><Link to="/resources">Add a verified resource</Link></small></>}</td>
        <td><span className={`recommendation-status ${item.is_completed?"is-complete":""}`}>{item.is_completed?"Completed":"In progress"}</span></td>
        <td><button className="complete-button" disabled={busyId===item.id} onClick={()=>toggle(item)}>{busyId===item.id?<LoaderCircle className="spin" size={13}/>:item.is_completed?<Check size={13}/>:null}{item.is_completed?"Reopen":"Mark complete"}</button><details className="recommendation-details"><summary>Activity and rationale</summary><p>{item.why_it_matters||"This skill appears in the target job requirements."}</p><p>{item.learning_activity}</p><p>{item.project_idea}</p></details></td>
      </tr>)}
    </tbody></table>{!visibleItems.length&&<div className="panel empty-panel"><span><Sparkles size={18}/></span><p>No recommendations match the selected filters. Analyses with missing skills appear here.</p></div>}</div>
  </>;
}

export function ReportsPage() {
  const [items, setItems] = useState([]), [selected, setSelected] = useState(""), [error, setError] = useState(""), [busy, setBusy] = useState(false), [success, setSuccess] = useState("");
  useEffect(() => { getHistory().then((data) => { setItems(data.items); if (data.items.length) setSelected(String(data.items[0].id)); }).catch((e) => setError(errorMessage(e))); }, []);
  async function download() { if (!selected) return; setBusy(true); setError(""); try { const blob = await createReport(Number(selected)); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `placement-analysis-${selected}.pdf`; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); setSuccess("PDF report downloaded."); } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); } }
  async function exportCsv() {
    if (!items.length) return;
    setBusy(true); setError(""); setSuccess("");
    try {
      const blob = await exportHistoryCsv();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a"); link.href = url; link.download = "placement-analysis-history.csv"; link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000); setSuccess("CSV export downloaded.");
    } catch (e) { setError(errorMessage(e)); } finally { setBusy(false); }
  }
  const selectedRecord = items.find((item) => String(item.id) === selected);
  return <><Heading eyebrow="REPORT CENTER" title={<>Reports that show<br /><span className="gradient-text">the whole picture.</span></>} text="Download a PDF for a saved analysis or export up to the latest 500 analyses as CSV." /><Notice error={error} success={success} /><div className="report-layout"><section className="panel report-selector"><span className="panel-kicker">INDIVIDUAL REPORT</span><h2>Select a saved analysis</h2><p>Reports include profile and job details, skill match, gaps, recommendations, and any saved model result.</p><select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}><option value="">Choose analysis</option>{items.map((a) => <option key={a.id} value={a.id}>#{a.id} · {a.student_name || a.student_id || "Candidate"} → {a.job_title || "Job"}</option>)}</select>{selectedRecord && <div className="report-preview"><div><span>SKILL MATCH</span><strong>{selectedRecord.skill_match_pct == null ? "—" : `${selectedRecord.skill_match_pct}%`}</strong></div><div><span>MISSING SKILLS</span><strong>{selectedRecord.missing_skills?.length || 0}</strong></div><div><span>SYNTHETIC LABEL</span><strong>{selectedRecord.predicted_label == null ? "Unavailable" : selectedRecord.predicted_label ? "Synthetic suitable" : "Synthetic unsuitable"}</strong></div></div>}<p className="rec-context">{selectedRecord?.model_notice}</p><button className="primary-action" disabled={!selected || busy} onClick={download}>{busy ? <LoaderCircle className="spin" size={15} /> : <Download size={15} />} Download PDF</button></section><section className="panel report-selector"><span className="panel-kicker">BULK EXPORT</span><h2>Analysis results as CSV</h2><p>Export the latest 500 analysis history records for review in a spreadsheet.</p><div className="export-count"><strong>{items.length}</strong><span>latest saved records (max 500)</span></div><button className="quiet-button" disabled={!items.length} onClick={exportCsv}><Download size={14} /> Download CSV</button></section></div></>;
}

export function AboutPage() {
  return <><Heading eyebrow="ABOUT THIS PROJECT" title={<>What the system can<br /><span className="gradient-text">and cannot tell you.</span></>} text="A transparent overview of the Placement Intelligence prototype and its source data." /><div className="about-grid"><section className="panel about-card"><span className="panel-kicker">PROJECT PURPOSE</span><h2>Match skills to job requirements.</h2><p>The app compares exact skill phrases in a student profile and job description, calculates gaps, and can call a trained suitability classifier only when matching model artifacts are present.</p></section><section className="panel about-card"><span className="panel-kicker">DATA SOURCE</span><h2>Student–job dataset</h2><p>The workspace and record forms cover the CSV?s 31 columns. Matched and missing skills, counts, and skill match are derived from exact phrase overlap. In all 799,020 source rows, experience_eligible exactly matches is_fresher_friendly. The synthetic target is shown only as a model output; added SQLite records are kept separate from source CSV counts.</p></section><section className="panel about-card caution"><span className="panel-kicker">MODEL LIMITATION</span><h2>Synthetic target, historical evaluation.</h2><p>The target column is <code>suitability_label_synthetic</code>. Notebook results describe an experimental grouped split and do not represent real placement outcomes, hiring decisions, or employment probability.</p></section></div><Link to="/model-room" className="text-link">View historical model metrics <ArrowRight size={14} /></Link></>;
}
