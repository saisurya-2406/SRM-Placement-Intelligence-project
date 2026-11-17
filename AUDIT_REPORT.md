# SRM Placement Intelligence: Integration and Execution Report

Audit date: 2026-11-17 (Asia/Kolkata)

Project root: `C:\Users\User\Downloads\SRM-Placement-Intelligence\SRM-Placement-Intelligence\SRM-Placement-Intelligence`

## Initial integration report (historical; superseded by the current status below)

| Task | Status | Evidence | Issues |
|---|---|---|---|
| Local Python/NumPy environment | **COMPLETE** | Created a clean project `.venv` on Python 3.13.5. Imports pass for NumPy 2.5.5, Pandas 3.0.6, scikit-learn 1.6.1, SciPy 1.18.1, Flask 3.1.3, Flask-Cors 6.0.5, and joblib 1.6.0. Pins are recorded in `backend/requirements.txt`. | Python 3.11/3.12 are not installed. scikit-learn 1.6 supports standard Python 3.13, and this exact bundle was loaded and exercised on 3.13.5. If a strict 3.12 interpreter is required, use the command in the setup section. |
| ML model integration | **COMPLETE** | All five classifiers, training medians, scaler, and 20-feature configuration loaded. Registry reports `ready: true`. A real SVM API prediction returned synthetic label 0 and decision score `-1.74065`; missing numeric values were imputed from saved training medians. | The target is synthetic. The SVM decision score is not a probability; the recorded test precision for the positive class is about 18.1%. |
| Frontend startup | **COMPLETE** | `npm run dev` starts Vite 6.4.6 at `http://127.0.0.1:5173/`. Development HTML and transformed app/API modules returned HTTP 200. `npm run build` succeeded. Chrome loaded the real development app. | The browser could not load optional Google Fonts due network policy (`net::ERR_NETWORK_ACCESS_DENIED`); CSS fallback fonts render. Build warns that its ~750 kB JavaScript chunk is above Vite's 500 kB threshold. |
| Backend startup | **COMPLETE** | The project `.venv` runs Flask at `http://127.0.0.1:5000`; live health reports database ready and all five algorithms available. Dataset API reports 799,020 rows. | Flask uses the built-in debug server for local development. |
| Frontend-backend integration | **COMPLETE** | Chrome observed successful API responses, created student and job records through UI forms, loaded them into workspace, submitted analysis, displayed a real SVM result, reloaded saved history, completed a recommendation, and downloaded PDF/CSV. CORS allowed the configured frontend origin. | External font requests are blocked in this environment; API requests succeeded. |
| API verification | **COMPLETE** | Flask test client exercised all route groups in 42 requests, including CRUD, aliases, suggestion, extraction, analysis, prediction, model diagnostics, reports, recommendations, CORS, and expected 400/404 errors. | Test inputs cover important paths and representative invalid inputs; they do not enumerate every possible validation string or concurrent database case. |
| Complete application testing | **COMPLETE** | Browser-tested dashboard, all navigation pages, student/job forms, saved-record selectors, skill analysis, actual inference, history persistence after reload, learning completion, model comparison, and PDF/CSV downloads. At 390 px viewport, no horizontal overflow was found. | UI-level checks cover primary workflows; uncommon browser, OS, and data-volume conditions remain outside this local run. |
| Final documentation | **COMPLETE** | `README.md`, this report, and pinned backend requirements describe the current runtime, APIs, model limitations, startup, tests, and demo. | Keep the report current if dependencies or model artifacts change. |
| Demonstration preparation | **COMPLETE** | Commands, URLs, sample student/job fields, expected skill match, live model output type, and presentation caveat are below. | Do not describe the synthetic label as an actual placement prediction. |

## Feature inventory

| Feature | Frontend | Backend/API | Persistence or ML | Verification |
|---|---|---|---|---|
| Dashboard and dataset overview | `Overview` in `frontend/src/App.jsx` | `/api/dashboard`, `/api/dataset-info`, `/api/health`, `/api/model-info`, `/api/model-performance` | Dataset index, SQLite aggregates, stored notebook metrics | Browser render and live 200 responses |
| Student directory | `StudentsPage` in `frontend/src/pages/ManagementPages.jsx` | `/api/students` list/create/update/delete and `/api/students/<id>` | SQLite `students`; dataset branch validation | UI create, list and workspace load; API update/delete and invalid input |
| Job library | `JobsPage` in `frontend/src/pages/ManagementPages.jsx` | `/api/jobs` list/create/update/delete and `/api/jobs/<id>` | SQLite `jobs`; optional literal skill extraction | UI create/list and workspace load; API update/delete and invalid input |
| Similar profile suggestion | Workspace button in `frontend/src/App.jsx` | `/api/suggest-profile` | Anonymized candidate examples from dataset index; user must review/copy | API request passed; manual UI suggestion copy was not separately exercised |
| Job-description skill extraction | Workspace “Find skills” action | `/api/analyze-job-description`, legacy `/api/extract-skills` | Literal phrases from dataset skill vocabulary | API responses passed |
| Skill overlap and gap analysis | Workspace result cards | `/api/match-skills`, `/api/analyze-skills`, `/api/analyze-skill-gap`, `/api/analyze` | Exact case-insensitive phrase overlap; no inferred skill weights | UI showed 2/3 matched, Tableau gap, 66.67% |
| Saved analysis workflow | Workspace and History pages | `/api/analyze`, `/api/analysis-history`, delete route | SQLite analyses, gaps, and recommendations | UI analysis and browser reload retained saved row |
| ML inference and comparison | Workspace prediction card; Model Comparison page | `/api/predict`, `/api/model-info`, `/api/model-performance`, `/api/compare-models` | Five saved classifiers plus training medians and scaler | Real SVM result rendered; five historical metric rows loaded |
| Learning recommendations | Learning page | `/api/learning-recommendations`, PATCH completion | SQLite rows derived from missing skills; priority stays unranked | Browser “Mark complete” action persisted |
| Reports | Reports page | `/api/generate-report`, `/api/export-analysis.csv` | Saved SQLite analysis snapshots | Chrome downloaded PDF and CSV; PDF starts `%PDF`, CSV contained saved candidate |
| History search/delete | History page | `/api/analysis-history`, delete route | SQLite analyses | Load/search/read covered; delete covered via API |
| About/limitations | About page and app notices | Model config and diagnostics | Synthetic target notice | Rendered in browser; synthetic disclaimer remains visible |

## Changes made

- Recreated the project-local `.venv` cleanly. The old environment had Python 3.14 NumPy binaries in a Python 3.13 virtualenv, producing a compiled-extension import failure.
- Pinned direct runtime dependencies in `backend/requirements.txt` and installed scikit-learn 1.6.1, matching `model/feature_config.json`.
- Updated `backend/model.py` to pass named feature columns into a scaler fitted with feature names and to report the actual preprocessing/runtime error.
- Updated `backend/app.py` to impute omitted or blank numeric prediction inputs with the saved training medians and to normalize notebook-native evaluation metric names for the frontend. Previously `/api/model-performance` and `/api/compare-models` returned HTTP 500 because they expected keys absent from the saved metric config.
- Updated `frontend/src/App.jsx` to include `branch` in workspace analysis requests. It was validated in the form but omitted from the request, which prevented manual UI predictions.
- Updated the landing-page model notice so it no longer says predictions are disabled when the matching runtime is installed.
- Configured all Vite scripts to use the runner config loader; `npm run dev` and `npm run build` now work with the project scripts.
- Corrected the README's notebook filenames, environment guidance, model state, and execution instructions.

## Architecture and request flow

```text
React pages/components
  -> Axios API client (VITE_API_URL or http://127.0.0.1:5000/api)
  -> Flask routes in backend/app.py; CORS uses PLACEMENT_CORS_ORIGINS
  -> SQLite for managed records/analyses; dataset_index.json for source summaries and skill vocabulary
  -> ModelRegistry loads the five saved estimators, training medians, and scaler for prediction
  -> JSON, PDF, or CSV response rendered or downloaded by the UI
```

The source dataset index reports 799,020 student/job rows, 79,902 students, and 5,393 jobs. Source CSV summaries and managed SQLite records remain separate. Skill matching uses exact phrase overlap; job-description terms are literal matches against the index vocabulary. Recommendations are based on missing skills and intentionally remain unranked because the data has no per-skill importance weights.

## Environment and setup

The active interpreter during verification was Python 3.13.5. `py -0p` found no Python 3.11 or 3.12 installations. The verified project environment uses Python 3.13.5 with the following package versions:

| Package | Version |
|---|---:|
| NumPy | 2.5.5 |
| Pandas | 3.0.6 |
| scikit-learn | 1.6.1 |
| SciPy | 1.18.1 |
| Flask | 3.1.3 |
| Flask-Cors | 6.0.5 |
| joblib | 1.6.0 |

The scikit-learn 1.6 documentation lists Python 3.9–3.13 support, and the model artifacts loaded and predicted successfully under Python 3.13.5. If you need Python 3.12 specifically, install it and create another environment:

```powershell
winget install --exact --id Python.Python.3.12
py -3.12 -m venv .venv312
.\.venv312\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt
```

References: [scikit-learn 1.6 installation guide](https://scikit-learn.org/1.6/install.html), [official Python Windows downloads](https://www.python.org/downloads/windows/), [Microsoft winget package manifest](https://github.com/microsoft/winget-pkgs/tree/master/manifests/p/Python/Python/3/12).

For the currently verified project environment, activate it from the project root and install the pinned requirements:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -c "import numpy, pandas, sklearn, scipy, flask, joblib; print(numpy.__version__, pandas.__version__, sklearn.__version__, scipy.__version__, flask.__version__, joblib.__version__)"
```

`backend/requirements.txt` pins the complete installed Python stack, including transitive dependencies. A fresh install requires access to PyPI.

## Model notes

The model bundle requires an exact 20-feature order: ten numeric student fields and ten one-hot categorical fields. `ModelRegistry` checks feature order, categories, estimator feature counts/classes, training medians, scaler dimensions/names, and the recorded scikit-learn version. All five estimator files, `train_medians.pkl`, `standard_scaler.pkl`, and `feature_config.json` are present and passed those checks.

The target `suitability_label_synthetic` is not actual placement or hiring success. The SVM output exposes a decision score rather than probabilities. Tree/KNN/Naive Bayes score fields are class scores, not calibrated employment probabilities. In the recorded grouped test split, the selected SVM positive-class precision is about 18.1%, so this remains an experimental research prototype rather than a hiring decision tool.

## Verification evidence

- Python imports passed in the clean `.venv`; model registry status reported all five algorithms, medians, and scaler ready.
- Live backend returned HTTP 200 for health, model info, dataset info, and model performance. Prediction returned HTTP 200 with the actual SVM result and synthetic-target notice.
- A prediction with missing numeric inputs returned a real result after median imputation. Invalid numeric range and category returned HTTP 400.
- Flask test client made 42 requests across all 34 Flask routes/aliases and all API feature groups. Valid CRUD, profile suggestion, skill extraction/matching/gaps, save/history, recommendation completion, diagnostics, model inference, PDF/CSV, CORS, and expected validation/not-found statuses passed.
- `npm run build` passed: 2,051 modules transformed; CSS 39.81 kB and JS about 750 kB (214.93 kB gzip). Vite reports a large-chunk warning.
- `npm run dev` started at `http://127.0.0.1:5173`. Chrome loaded all main pages and its network panel showed frontend API responses. Workspace analysis sent `branch`, saved an analysis, rendered `Synthetic unsuitable (0)` with SVM decision score `-1.7407`, and showed a 66.67% skill match.
- Chrome tested student/job creation via UI, saved-record loading, history after browser reload, recommendation completion, five-row model comparison, and PDF/CSV downloads. A 390 px viewport had no horizontal overflow.
- Browser console errors were limited to blocked external Google Fonts requests (`net::ERR_NETWORK_ACCESS_DENIED`). No frontend API request failed. System font fallbacks render the UI.

## Local demonstration

Terminal 1, from the project root:

```powershell
.\.venv\Scripts\Activate.ps1
$env:PLACEMENT_DB_PATH = "$env:TEMP\placement-intelligence-demo.sqlite3"
python -m backend.app
```

Terminal 2:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`. API health/docs are `http://127.0.0.1:5000/api/health` and `http://127.0.0.1:5000/api/docs`. SQLite initializes at startup; the included CSV index is already built.

### Demonstration workflow

1. Show the dashboard dataset counts, `Predictions ready` state, and model metrics.
2. Add a student: ID `DEMO-001`, name `Demo Candidate`, branch `CSE`, CGPA `8.4`, coding `82`, aptitude `76`, communication `78`, logical reasoning `80`, mock interview `75`, backlogs `0`, GitHub repos `4`, internships `1`, projects `3`, skills `Python, SQL`.
3. Add a job: company `Example Analytics`, title `Data Analyst`, category `Data Analyst`, work mode `Hybrid`, required skills `Python, SQL, Tableau`.
4. Load the saved student/job in Match Workspace and submit. Expected skill overlap: Python and SQL; missing skill: Tableau; skill match: 66.67%. The live model result is a synthetic label and model-specific score.
5. Open Learning Path, mark Tableau complete, review Analysis History, then download PDF and CSV from Reports.
6. In Model Comparison, explain that the evaluation metrics are historical grouped-split results and the label is synthetic.

The exact prediction value depends on the chosen profile and model. Do not promise placement based on it.
# Career Intelligence Expansion (17 Nov 2026)

The career workflow was added alongside the existing student/job management, match workspace, five-model diagnostics, recommendations, history, and reports. Database changes are additive `ALTER TABLE` migrations; roadmap activities and saved resources use related SQLite tables and foreign keys.

## Feature verification

| Feature | Implementation | Backend | Frontend | Testing |
|---|---|---|---|---|
| Student profile | Degree, specialization, graduation year, experience, interests, target roles, projects, certifications added to existing profile | Validated student CRUD and additive SQLite migration | Extended Students form | Flask test-client create/read path; production frontend build |
| Job matching | Dedicated Career Intelligence opportunity explorer | `/api/job-matches` | Saved student/job selection and comparison rows | Exact-match and configured-rule path exercised |
| Eligibility analysis | Degree, CGPA, branch, experience/fresher, certification requirements are independent mandatory rules | `/api/job-matches` | Reasons shown next to each opportunity | Test confirms independent CGPA, branch, experience, certification failures |
| Skill gap analysis | Existing exact case-insensitive matching reused | Existing `/api/match-skills`, plus job matches | Matched/missing tags and coverage | Python API workflow asserted missing Power BI |
| Learning roadmap | Six stages; missing skills drive foundations, exercises, project tasks; interview/readiness tasks are role-bound | Roadmap/activity tables and create/read/update/recalculate APIs | Timeline, per-activity completion, recalc | Generated, marked complete, reloaded and recalculated via Flask client |
| Course recommendations | Curated catalog of official Python, PostgreSQL, Microsoft Learn paths | `/api/resources`; resource save persists | Filterable provider resource shelf and save action | Resource list and persistence tested |
| Certifications | Official Microsoft PL-300 credential listed with region-varying fee note; student/job cert names stored | Certification eligibility and resource catalog | Certification requirement appears in readiness/roadmap | API exercised; provider information checked against Microsoft Learn |
| Interview preparation | Generated role/skill/project practice prompts labeled as generated | `/api/interview-prep` | Topic-grouped practice center | Endpoint tested for saved student/job |
| Progress tracking | Roadmap task completion and roadmap-specific saved resources persist with timestamps | SQLite activity/resource tables | Completion controls; saved resource links appear in that roadmap | Completion and roadmap resource link survived API reload |
| Career analytics | Profile completeness, job match categories, project/cert counts, roadmap progress | `/api/career-analytics/<id>` | Readiness visualization and metric definitions | Endpoint tested against persisted activity |
| ML prediction | Five original estimators and existing preprocessing preserved | Existing `/api/predict`, diagnostics, and model bundle untouched | Existing workspace/model room preserved | Prior browser/API audit documented above; new career matches do not call ML |
| PDF/CSV reports | Existing report generation and export preserved | Existing report endpoints | Existing report page preserved | Prior browser audit documented above; production build passes |

## New career API routes

`GET /api/job-matches?student_id=<id>` returns configured eligibility and exact phrase skill coverage separately. `POST /api/roadmaps` creates a student/job-specific roadmap. `GET /api/roadmaps`, `GET /api/roadmaps/<id>`, `PATCH /api/roadmap-activities/<id>`, and `POST /api/roadmaps/<id>/recalculate` persist/read progress. `GET /api/resources`, `POST /api/resources/<resource_id>/save`, and `GET /api/saved-resources` expose the curated catalog. `GET /api/interview-prep?student_id=<id>&job_id=<id>` returns generated practice prompts. `GET /api/career-analytics/<student_id>` provides derived readiness measures.

## Expansion verification run

- `python -m py_compile backend/app.py backend/database.py backend/career_intelligence.py` passed.
- `python -m unittest discover -s backend/tests -v` passed all 3 integration tests. The suite independently invoked all five available classifiers and verified legacy PDF/CSV exports plus profile/job creation, independent eligibility reasons, exact skill gaps, personalized roadmap generation and persisted completion, readiness recalculation, interview prep, analytics, official certification resource selection, and saved resource persistence.
- `npm run build` passed. Vite reports a bundle-size advisory because the chart-heavy frontend produces a JavaScript chunk over 500 kB; this is an optimization warning, not a build error.
- Headless Chrome against the production preview rendered `/career`, including the Career Intelligence heading and resource navigation. Layout checks across multiple viewport sizes and interactive browser clicks were not automated in this pass.
- Resource references use official provider documentation and Microsoft Learn; links do not claim that external course availability will remain unchanged. Microsoft lists certification exam pricing by region, so the UI does not show one universal fee.

## Scope and remaining limitations

- This is a locally managed opportunity library, not a live job feed. No job postings are fabricated or imported.
- The verified resource catalog is intentionally limited to provider pages in the repository. For uncovered skills, generated practice/project work remains available and the UI does not invent a course.
- Profile skills are self-reported without proficiency ratings. Project/certification records are free text; marking a learning activity complete does not silently add a skill or certify a credential.
- Roadmap duration is not estimated where the provider has not published one. The saved catalog currently supports a compact set of verified official resources.
- The interview prompts are generated from role/profile context and are not company interview questions. Company-specific research and real mock-interview scoring are not implemented.
- The additional Career Intelligence interface was production-build checked and backend-workflow tested. Full browser automation of every new screen, viewport, click target, and external link was not run in this expansion pass; the earlier browser run covers the unchanged existing pages only.

# Complete Source and Runtime Audit (17 Nov 2026)

This pass re-read the source, inspected the actual configured SQLite file read-only before applying the normal additive startup migration, checked the raw supplied CSV, exercised the actual default DB using disposable records, verified all five loaded estimators and ran the repository's test/build/compile commands. No model training or artifact replacement was performed.

## Requested final status table

| Feature | Status | Evidence | Issues Fixed |
|---|---|---|---|
| Student Management | COMPLETE | Student form and Flask CRUD; two profiles created, retrieved, updated, and independently analyzed in integration tests; default DB workflow survived a fresh backend process | Added persistence/restart coverage; schema changes are additive |
| Job Management | COMPLETE | Job CRUD APIs/forms; job requirements and optional eligibility constraints used by matching | Added required-degree rule and exposed eligibility fields in form |
| Five ML Classifiers | COMPLETE | Health reports all five ready with no model errors; integration suite calls each saved estimator independently | No retraining; unused legacy `median_imputer.pkl` identified |
| New Student Prediction | COMPLETE | Two newly saved students selected by record ID, separately matched, predicted by actual SVM, and persisted to analysis history | Documented that profile registration saves only; prediction is explicitly requested in Match Workspace |
| Skill Matching | PARTIALLY COMPLETE | Exact phrase matching, case folding, duplicate/space normalization, missing/matched sets, and 60% example tested | Alias support is not implemented; clarified exact-match limit and corrected eligibility-method copy to include degree |
| SQLite Storage | COMPLETE | Default `data/placement_intelligence.sqlite3` inspected; integrity and foreign keys pass; disposable two-student/job/analysis/roadmap workflow survives new backend process | Applied additive migrations; documented relationships and active DB-path mismatch |
| Career Roadmaps | COMPLETE | Six stages generated from actual missing skills; activity completion/recalculation and saved resources persist and reload | No fake opportunities/resources added |
| Learning Resources | PARTIALLY COMPLETE | Provider-owned official Python/PostgreSQL/Microsoft resources and PL-300 credential links; catalog and save flow tested | Catalog is intentionally small; other skills receive project activities but no invented links |
| Interview Preparation | PARTIALLY COMPLETE | Role/skills/projects generate practice prompts through `/api/interview-prep` | Prompts are generated, not company questions; individual prompt scoring and company research are absent |
| Analytics | PARTIALLY COMPLETE | Profile completeness, job readiness categories, skill coverage, and persisted-roadmap completion are API-backed | Proficiency and historical progress charts are unavailable because those data are not collected/stored |
| PDF Export | COMPLETE | Isolated integration test verifies downloadable response starts with `%PDF` | None found |
| CSV Export | COMPLETE | Export endpoint returns saved analyses and candidate identifiers; integration test checks response | CSV is capped at the latest 500 analyses |
| Frontend UI/UX | PARTIALLY COMPLETE | Career Intelligence production route/headline/tabs rendered in headless Chrome; API-connected design built and production bundle succeeds | Not every existing screen was comprehensively redesigned or browser-click audited in this pass |
| Responsive Design | PARTIALLY COMPLETE | Responsive CSS rules exist; previous audit recorded no overflow at 390 px for the old pages | Full current-page desktop/tablet/mobile viewport matrix was not executed |
| Backend APIs | COMPLETE | Health/docs, CRUD, matching, all classifiers, saved roadmap progress, resources, interview prompts, analytics, reports tested | Active server on port 5000 is using an environment-overridden temp DB and must be restarted to load the latest source edits |

## Database source of truth

Default source path: `C:\Users\User\Downloads\SRM-Placement-Intelligence\SRM-Placement-Intelligence\SRM-Placement-Intelligence\data\placement_intelligence.sqlite3`. `backend/config.py` uses this path unless `PLACEMENT_DB_PATH` is set. At the end of the audit the default DB has **0 students, 0 jobs, 0 analyses, 0 recommendations, 0 skill gaps, 0 roadmaps, 0 activities, and 0 saved resources**; integrity check is `ok`, foreign-key check is empty. The audit's disposable actual-DB test rows were deleted afterward.

The already-running local API on port 5000 is an older process with `PLACEMENT_DB_PATH` pointing at `C:\Users\User\AppData\Local\Temp\placement-final-live.sqlite3`; its API reports 1 student and 1 job (demo/test data). The Vite server on 5173 is also pre-existing. Therefore the live browser/API record count is not the same as the project's default database count. Starting Flask from the project root without that environment override selects the default project DB. The current active backend process needs a restart to load the final source; this audit did not stop a pre-existing process.

Tables and relationships are documented in the README Mermaid ER diagram. Actual schema inspection confirmed the tables: `students`, `jobs`, `analyses`, `skill_gaps`, `learning_recommendations`, `career_roadmaps`, `roadmap_activities`, and `saved_learning_resources`. Predictions are stored in `analyses`; no separate prediction table exists. Resources are a small Python catalog plus persisted saved IDs; interview prompts are generated rather than stored as a separate question table; readiness analytics are computed rather than persisted.

## Model and data evidence

The supplied `data/student_job_pairs_rebuilt.csv` exists (437,541,455 bytes). A streaming scan counted **799,020 rows**, **79,902 distinct student IDs**, synthetic target labels **735,306 zero / 63,714 one**. The target-generation formula is not in source, so it cannot be validated as a real placement outcome.

The five bundle files are `decision_tree.pkl`, `best_random_forest.pkl`, `svm.pkl`, `knn.pkl`, and `naive_bayes.pkl`. They are alternative classifiers for the same binary synthetic target, not five separate purposes: interpretable tree, bagged tree ensemble, RBF margin classifier (selected SVM), neighborhood method, and Gaussian probabilistic baseline. Ten numeric fields and ten one-hot categorical fields are built in the exact saved order. Inference uses `train_medians.pkl` and the fitted `standard_scaler.pkl`; `median_imputer.pkl` is present but not loaded by current runtime code. All five models predict through `/api/predict`; the new-student workflow uses `/api/analyze` and stores the actual returned selected model output. New student registration never retrains the models.

Recorded held-out metrics are historical and highly imbalanced: positive-class precision ranges from 15.13% (Gaussian Naive Bayes) to 33.98% (KNN), while KNN recall is only 10.94%; selected SVM precision is 18.14% at 91.88% recall. These scores classify the supplied synthetic label and are not placement probabilities.

The Colab-generated training export was inspected but not re-executed. It imports `google.colab`, reads `/content/student_job_pairs_rebuilt.csv`, and is not a verified standalone local training command. Existing models were instead verified through runtime loading and fresh inference; no artifacts were overwritten.

## Final commands and results

- `python -m unittest discover -s backend/tests -v`: **7 tests passed** (student/job CRUD and validation, two-student data isolation, restart persistence, exact-skill edge cases, all five models, resource/roadmap/interview/analytics, PDF and CSV).
- `python -m compileall -q backend`: **passed**.
- `npm run build`: **passed**; Vite warns that the minified JS chunk exceeds 500 kB.
- Headless Chrome loaded `/career` from the production preview with the career heading and resource navigation. Full interactive browser click-through and multi-viewport checks were not completed.
- Authentication is **not implemented**. This local prototype has no login or per-user authorization boundary.
- Current aliases are not canonicalized (`PowerBI` does not equal `Power BI`); matching is case-insensitive exact phrase overlap and the UI/API states this. Additional controlled aliases can be added later with an explicit, testable dictionary.

# Implementation and verification follow-up (17 Nov 2026)

This follow-up supersedes the earlier incomplete statuses above for database selection, skill aliases, resource coverage, scored interviews, proficiency history, frontend bundle size, and responsive testing. Historical audit sections are retained as a record of what was true before implementation.

## Current status

| Area | Status | Evidence and remaining limits |
|---|---|---|
| Database selection and persistence | **COMPLETE** | The browser-test process initially used `PLACEMENT_DB_PATH` and `/api/health` exposed the temporary path; startup also logged a warning. That backend was stopped, the override was cleared, and the project backend was restarted. Live health now reports `project default`; the startup log names the resolved path. |
| Existing data | **PRESERVED** | Project DB read-only verification before and after restart: 1 student, 1 job, 5 analyses, 1 interview attempt, 32 catalog resources, integrity check `ok`. The one project interview row is in progress (`submitted_at` is null); no proficiency record is present. The separate original temp DB remains intact with 1 student, 1 job, 5 analyses, integrity check `ok`. |
| Skill matching | **COMPLETE** | Canonical aliases, case/whitespace normalization, de-duplication, empty-list handling, coverage math, and non-alias separation are covered by integration tests. `PowerBI`, `MS Excel`, `Structured Query Language`, and `ML` normalize to their canonical names; PostgreSQL remains distinct. |
| Learning resources | **UPDATED** | Seeded resources are stored in SQLite and recommendations are skill-driven from the selected student's gaps and configured job requirements. Custom roles and catalog entries are supported without role-specific source changes. Automated tests cover five domains plus an unseeded custom role and custom resource. A browser check showed the custom Cloud Security resource recommended for a skill shared by two selected jobs. **Limit:** Custom URLs require administrator confirmation and HTTP(S) format, but the backend does not make an outbound request to verify destination content. |
| Mock interview workflow | **COMPLETE** | Create, role-based question generation, answer submission, transparent heuristic scoring/feedback, history, persistence, duplicate submission conflict, and student scoping pass isolated integration tests. Scores are disclosed as rule-based practice feedback, not AI, expert, or human assessment. |
| Skill proficiency history | **COMPLETE** | Check-ins store skill, prior/current self-rating, date, and student-reported learning progress. Readiness analytics and the visualization use persisted check-ins. Integration tests exercise record/reload and student isolation. Values are self-assessments, not validated tests. |
| Five ML classifiers | **PRESERVED / PASS** | Integration regression exercises Decision Tree, Random Forest, SVM, KNN, and Gaussian Naive Bayes. Health reports all five available with preprocessing ready. No retraining, relabeling, or model artifact changes were made. |
| Exports and persistence | **PASS** | Isolated tests cover restart persistence plus PDF response signature and CSV export. |
| Responsive UI | **PARTIAL SMOKE TEST** | The Career Intelligence comparison rendered at desktop, tablet, and mobile sizes. In the latest fresh mobile check at 390 CSS px, six consecutive measurements reported `clientWidth=375` and `scrollWidth=375`; body/root measured 375.2 CSS px due to fractional viewport sizing. One earlier sample reported 1px overflow, but this was not reproduced in the latest check, so no persistent component overflow was identified and no global clipping rule was added. **Limit:** Full all-route, all-control responsive verification remains incomplete. |
| Frontend performance | **IMPROVED** | Route-level lazy loading and isolated lazy chart components moved Recharts out of the entry chunk. Previous entry bundle was 725.67 kB; latest verified build entry is 290.38 kB (92.52 kB gzip), with Recharts in a 436.70 kB async chunk (117.54 kB gzip). This reduces the entry bundle by about 60%; no functionality was removed. |
| Authentication | **OPTIONAL FUTURE WORK** | Authentication and authorization are intentionally not implemented for the requested local academic demo. Do not expose the app as a public or multi-user service without them; API student scoping is not authentication. |
| Settings | **NOT IN SCOPE** | No Settings route exists; configuration is by documented environment variables. No settings page was added. |

## Database source and schema

The configured project default and active backend database after restart are:

`C:\Users\User\Downloads\SRM-Placement-Intelligence\SRM-Placement-Intelligence\SRM-Placement-Intelligence\data\placement_intelligence.sqlite3` (`project default`)

Read-only inspection verified the project database contains `students`, `jobs`, `analyses`, `skill_gaps`, `learning_recommendations`, `career_roadmaps`, `roadmap_activities`, `saved_learning_resources`, `learning_resource_catalog`, `mock_interview_attempts`, and `skill_proficiency_history`. Additive schema changes include the resource catalog table, optional job skills, and the learning-recommendation requirement type. The browser-test process had used `C:\Users\User\AppData\Local\Temp\srm-career-ui-b4996feb83a24a12899a3fc515bd981a.sqlite3`; health exposed the override, the process was stopped, and a clean project-default backend was started. The project database passed `PRAGMA integrity_check` before and after restart. Counts remained 1 student, 1 job, 5 analyses, 1 interview attempt, and 32 catalog resources; proficiency history has zero records. Automated tests used isolated temporary SQLite files for full create/submit/history/proficiency/persistence checks. The older temp database at `C:\Users\User\AppData\Local\Temp\placement-final-live.sqlite3` remains intact. No existing records or database files were deleted.

For GitHub publishing, `data/student_job_pairs_rebuilt.csv`, `data/dataset_index.json`, and SQLite files are excluded because they contain student identifiers or student-level academic/skills information. The training notebook outputs were cleared while preserving all source cells. A clone needs an authorized local dataset and must rebuild its dataset index before dataset-backed profile suggestions work.

The README contains PowerShell commands to stop the backend bound to port 5000 by resolved process ID, clear an inherited override, and start the backend/frontend from this checkout.

## Verification run

- `.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v`: **14 tests passed**.
- `python -m compileall -q backend`: **passed**.
- `npm run build`: **passed**; 2,058 modules transformed. Entry bundle: 290.38 kB (92.52 kB gzip); lazy chart chunk: 436.70 kB (117.54 kB gzip).
- All five classifier inference paths and PDF/CSV export cases passed in the integration suite.
- Skill alias/coverage and role-independent resource recommendation tests passed across Data Analytics, Software Development, Cloud/DevOps, Cybersecurity/Networking, Business Analysis, and a custom role using its actual saved requirements.
- Multi-job comparison tests cover shared and unique skill gaps, optional requirements, unmatched skills, duplicate avoidance, custom catalogue resources, different student skill profiles, and SQLite persistence.
- Mock interview question creation, scoring, feedback, attempt history, duplicate submission rejection, and student scoping passed.
- Proficiency tracking, historical comparison, readiness analytics, and persistence passed.
- Browser UI created a student, two custom-role jobs, and a custom resource in an isolated temporary database. The selected roles shared the missing required skill `Cloud Security`; the custom resource was shown as a recommendation for that skill. The second job showed its unique `Terraform` gap and optional `Docker` gap.
- Career Intelligence was measured at desktop (1440), tablet (768), and mobile (390) widths. The latest fresh mobile recheck produced six consecutive `scrollWidth=375` readings for a 375px layout viewport; the body/root's 375.2px width is fractional sizing rather than reproducible content overflow. One earlier sample reported a 1px overflow. No global clipping workaround was added. The run did not click every application control or verify external provider destinations.
- React Router emitted its two known v7 future-flag **warnings** during page reloads. No browser page exceptions were captured in the exercised flows. The browser request-context tool failed on a prior attempt; it was not used for API verification.

## Changed files

- Backend: `backend/config.py`, `backend/database.py`, `backend/app.py`, `backend/skill_matching.py`, `backend/career_intelligence.py`, and `backend/tests/test_career_workflow.py`.
- Frontend: `frontend/src/App.jsx`, `frontend/src/main.jsx`, `frontend/src/ModelCharts.jsx`, `frontend/src/index.css`, `frontend/src/responsive.css`, `frontend/src/ui-feedback.css`, `frontend/src/pages/CareerPages.jsx`, `frontend/src/pages/CareerWorkflows.css`, `frontend/src/pages/ManagementPages.jsx`, `frontend/src/pages/ResourceManagement.css`, and `frontend/src/services/api.js`.
- Documentation: `README.md` and this report.
- Data: `data/placement_intelligence.sqlite3` is the project-local database used at runtime; existing records were preserved and new schema was added.

## Exact local start commands

From the project root, in PowerShell, clear any accidental override and start Flask:

```powershell
Remove-Item Env:PLACEMENT_DB_PATH -ErrorAction SilentlyContinue
& '.\.venv\Scripts\python.exe' -m backend.app
```

In another PowerShell terminal:

```powershell
Set-Location .\frontend
npm run dev
```

Open `http://127.0.0.1:5173/`; verify the backend database path at `http://127.0.0.1:5000/api/health`.
