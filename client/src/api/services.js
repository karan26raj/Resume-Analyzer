import { apiRequest, uploadFile } from './client'

export const authApi = {
  register: (email, password) =>
    apiRequest('/auth/register', { method: 'POST', body: { email, password }, auth: false }),
  login: (email, password) =>
    apiRequest('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
  me: (options) => apiRequest('/auth/me', options),
}

export const systemApi = {
  health: (options) => apiRequest('/health', { ...options, auth: false }),
}

export const resumesApi = {
  list: (options) => apiRequest('/resumes/', options),
  get: (id, options) => apiRequest(`/resumes/${id}`, options),
  text: (id, options) => apiRequest(`/resumes/${id}/text`, options),
  remove: (id) => apiRequest(`/resumes/${id}`, { method: 'DELETE' }),
  upload: (file, onProgress) => uploadFile('/resumes/upload', file, { onProgress }),
  rewrite: (resumeId, jobId, { force = false } = {}) =>
    apiRequest('/resumes/rewrite', { method: 'POST', body: { resume_id: resumeId, job_id: jobId, force } }),
}

export const jobsApi = {
  list: (options) => apiRequest('/jobs', options),
  get: (id, options) => apiRequest(`/jobs/${id}`, options),
  create: (job) => apiRequest('/jobs', { method: 'POST', body: job }),
  remove: (id) => apiRequest(`/jobs/${id}`, { method: 'DELETE' }),
}

export const analysisApi = {
  list: (filters, options) => apiRequest('/analysis', { ...options, query: filters }),
  get: (id, options) => apiRequest(`/analysis/${id}`, options),
  match: (resumeId, jobId, { force = false } = {}) =>
    apiRequest('/analysis/match', { method: 'POST', body: { resume_id: resumeId, job_id: jobId, force } }),
}

export const recommendationsApi = {
  get: (limit = 8, options) => apiRequest('/recommendations', { ...options, query: { limit } }),
  jobs: ({ resumeId, limit = 10 } = {}, options) =>
    apiRequest('/recommendations/jobs', { ...options, query: { resume_id: resumeId || undefined, limit } }),
}

export const embeddingsApi = {
  indexResume: (resumeId) =>
    apiRequest('/embeddings/index', { method: 'POST', body: { resume_id: resumeId } }),
  indexJob: (jobId) => apiRequest('/embeddings/index', { method: 'POST', body: { job_id: jobId } }),
  search: ({ query, documentType, limit }) =>
    apiRequest('/embeddings/search', {
      method: 'POST',
      body: { query, document_type: documentType || null, limit },
    }),
}

export const interviewApi = {
  questions: (resumeId, jobId, { force = false } = {}) =>
    apiRequest('/interview/questions', { method: 'POST', body: { resume_id: resumeId, job_id: jobId, force } }),
}

export const assistantApi = {
  ask: ({ question, limit = 5, resumeId, jobId }) =>
    apiRequest('/assistant/ask', {
      method: 'POST',
      body: {
        question,
        limit,
        resume_id: resumeId || null,
        job_id: jobId || null,
      },
    }),
}
