import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api",
  timeout: 120000,
});

export const getHealth = () => api.get("/health").then((r) => r.data);
export const getModelInfo = () => api.get("/model-info").then((r) => r.data);
export const getModelPerformance = () => api.get("/model-performance").then((r) => r.data);
export const getDatasetInfo = () => api.get("/dataset-info").then((r) => r.data);
export const getDashboard = () => api.get("/dashboard").then((r) => r.data);
export const getStudents = (params = {}) => api.get("/students", { params }).then((r) => r.data);
export const createStudent = (data) => api.post("/students", data).then((r) => r.data);
export const updateStudent = (id, data) => api.put(`/students/${id}`, data).then((r) => r.data);
export const deleteStudent = (id) => api.delete(`/students/${id}`).then((r) => r.data);
export const getJobs = (params = {}) => api.get("/jobs", { params }).then((r) => r.data);
export const createJob = (data) => api.post("/jobs", data).then((r) => r.data);
export const updateJob = (id, data) => api.put(`/jobs/${id}`, data).then((r) => r.data);
export const deleteJob = (id) => api.delete(`/jobs/${id}`).then((r) => r.data);
export const analyzeJobDescription = (description) => api.post("/analyze-job-description", { job_description: description }).then((r) => r.data);
export const matchSkills = (data) => api.post("/match-skills", data).then((r) => r.data);
export const analyzeSkillGap = (data) => api.post("/analyze-skill-gap", data).then((r) => r.data);
export const analyze = (data) => api.post("/analyze", data).then((r) => r.data);
export const predict = (data) => api.post("/predict", data).then((r) => r.data);
export const compareModels = (algorithms) => api.post("/compare-models", { algorithms }).then((r) => r.data);
export const getHistory = (params = {}) => api.get("/analysis-history", { params }).then((r) => r.data);
export const deleteAnalysis = (id) => api.delete(`/analysis-history/${id}`).then((r) => r.data);
export const getRecommendations = (params = {}) => api.get("/learning-recommendations", { params }).then((r) => r.data);
export const updateRecommendation = (id, is_completed) => api.patch(`/learning-recommendations/${id}`, { is_completed }).then((r) => r.data);
export const createReport = (analysis_id) => api.post("/generate-report", { analysis_id }, { responseType: "blob" }).then((r) => r.data);
export const exportHistoryCsv = () => api.get("/export-analysis.csv", { responseType: "blob" }).then((r) => r.data);
export const suggestProfile = (profile) => api.post("/suggest-profile", { profile }).then((r) => r.data);
export const extractSkills = (description) => api.post("/analyze-job-description", { job_description: description }).then((r) => r.data);
export const getJobMatches = (student_id) => api.get("/job-matches", { params: { student_id } }).then((r) => r.data);
export const getCareerResources = (params = {}) => api.get("/resources", { params }).then((r) => r.data);
export const createCareerResource = (data) => api.post("/resources", data).then((r) => r.data);
export const saveCareerResource = (id, student_id, roadmap_id) => api.post(`/resources/${encodeURIComponent(id)}/save`, { student_id, roadmap_id }).then((r) => r.data);
export const createCareerRoadmap = (student_id, job_id) => api.post("/roadmaps", { student_id, job_id }).then((r) => r.data);
export const getCareerRoadmaps = (student_id) => api.get("/roadmaps", { params: { student_id } }).then((r) => r.data);
export const getCareerRoadmap = (id) => api.get(`/roadmaps/${id}`).then((r) => r.data);
export const updateRoadmapActivity = (id, is_completed) => api.patch(`/roadmap-activities/${id}`, { is_completed }).then((r) => r.data);
export const recalculateCareerRoadmap = (id) => api.post(`/roadmaps/${id}/recalculate`).then((r) => r.data);
export const getInterviewPrep = (student_id, job_id) => api.get("/interview-prep", { params: { student_id, job_id } }).then((r) => r.data);
export const createMockInterview = (student_id, job_id) => api.post("/mock-interviews", { student_id, job_id }).then((r) => r.data);
export const submitMockInterview = (id, answers) => api.post(`/mock-interviews/${id}/submit`, { answers }).then((r) => r.data);
export const getMockInterviews = (student_id) => api.get("/mock-interviews", { params: { student_id } }).then((r) => r.data);
export const recordSkillProficiency = (data) => api.post("/skill-proficiency", data).then((r) => r.data);
export const getSkillProficiency = (student_id) => api.get("/skill-proficiency", { params: { student_id } }).then((r) => r.data);
export const getCareerAnalytics = (student_id) => api.get(`/career-analytics/${student_id}`).then((r) => r.data);

export function errorMessage(error) {
  if (error?.response?.data instanceof Blob) return "The server could not complete this request.";
  return error?.response?.data?.error || error?.message || "The request could not be completed.";
}
