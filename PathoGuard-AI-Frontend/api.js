/**
 * PathoGuard-AI — Centralized API Communication Layer
 * 
 * Provides a robust, unified interface for all frontend communication with the FastAPI backend.
 * Handles base URLs, request timeouts, network errors, loading states, retries,
 * and live connection state broadcasting.
 */

(function () {
  'use strict';

  const DEFAULT_BACKEND_URL = 'http://127.0.0.1:8000';
  const STORAGE_KEY_BASE_URL = 'pathoguard_backend_url';

  class PathoGuardApiClient {
    constructor() {
      this.baseUrl = (typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY_BASE_URL) : null) || DEFAULT_BACKEND_URL;
      this.sessionToken = (typeof localStorage !== 'undefined' ? localStorage.getItem('pathoguard_session_token') : null);
      this.connectionState = 'connecting'; // 'connected' | 'connecting' | 'disconnected'
      this.lastHealthCheck = null;
      this.listeners = [];
      this.timeoutMs = 6000; // 6-second default timeout
    }

    /**
     * Obtains or refreshes a cryptographically signed HMAC-SHA256 session token
     */
    async ensureSession(userId = null) {
      if (this.sessionToken) return this.sessionToken;
      try {
        const res = await this.request('/api/v1/auth/session', {
          method: 'POST',
          body: JSON.stringify({ user_id: userId })
        });
        if (res && res.token) {
          this.sessionToken = res.token;
          if (typeof localStorage !== 'undefined') {
            localStorage.setItem('pathoguard_session_token', res.token);
          }
          return res.token;
        }
      } catch (e) {
        console.warn('[API Layer] Session acquisition warning:', e.message);
      }
      return null;
    }

    /**
     * Get active backend base URL
     */
    getBaseUrl() {
      return this.baseUrl;
    }

    /**
     * Update backend base URL and trigger immediate health re-check
     */
    setBaseUrl(url) {
      const cleanUrl = (url || DEFAULT_BACKEND_URL).trim().replace(/\/+$/, '');
      this.baseUrl = cleanUrl;
      localStorage.setItem(STORAGE_KEY_BASE_URL, cleanUrl);
      return this.checkHealth();
    }

    /**
     * Register listener for connection state changes: ('connected'|'connecting'|'disconnected', details)
     */
    onConnectionChange(callback) {
      if (typeof callback === 'function') {
        this.listeners.push(callback);
        // Immediately notify with current state
        try {
          callback(this.connectionState, this.lastHealthCheck);
        } catch (e) {
          console.error('[API Layer] Error in listener invocation:', e);
        }
      }
    }

    /**
     * Internal state broadcaster
     */
    _notifyState(state, data = null) {
      this.connectionState = state;
      if (data) this.lastHealthCheck = data;
      this.listeners.forEach((fn) => {
        try {
          fn(state, data);
        } catch (err) {
          console.error('[API Layer] State broadcast error:', err);
        }
      });
    }

    /**
     * Unified HTTP request wrapper with AbortController timeout & error classification
     */
    async request(endpoint, options = {}) {
      const url = `${this.baseUrl}${endpoint}`;
      const timeout = options.timeout || this.timeoutMs;
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeout);

      const headers = {
        'Accept': 'application/json',
        ...(this.sessionToken ? { 'Authorization': `Bearer ${this.sessionToken}` } : {}),
        ...(options.headers || {})
      };

      // Set JSON header only if body is not FormData
      if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
        headers['Content-Type'] = 'application/json';
      }

      try {
        const response = await fetch(url, {
          ...options,
          headers,
          signal: controller.signal
        });
        clearTimeout(timer);

        let data;
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          data = await response.json();
        } else {
          const text = await response.text();
          data = { message: text };
        }

        if (!response.ok) {
          const message = data.message || data.detail || `Server returned HTTP status ${response.status}`;
          const err = new Error(message);
          err.status = response.status;
          err.data = data;
          err.endpoint = endpoint;
          throw err;
        }

        return data;
      } catch (err) {
        clearTimeout(timer);
        if (err.name === 'AbortError') {
          const timeoutErr = new Error(`Request timed out after ${timeout / 1000}s while accessing ${endpoint}`);
          timeoutErr.status = 408;
          timeoutErr.isTimeout = true;
          timeoutErr.endpoint = endpoint;
          throw timeoutErr;
        }
        if (!err.status) {
          const netErr = new Error(`Cannot reach PathoGuard backend at ${this.baseUrl}. Please check that FastAPI is running.`);
          netErr.status = 0;
          netErr.isNetworkError = true;
          netErr.endpoint = endpoint;
          throw netErr;
        }
        throw err;
      }
    }

    /**
     * Resilient fetch with exponential backoff for idempotent operations
     */
    async fetchWithRetry(endpoint, options = {}, maxRetries = 2) {
      let lastError;
      for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
          return await this.request(endpoint, options);
        } catch (err) {
          lastError = err;
          if (attempt < maxRetries && (err.isNetworkError || err.isTimeout || (err.status >= 500))) {
            const delayMs = 300 * Math.pow(2, attempt);
            await new Promise((r) => setTimeout(r, delayMs));
            continue;
          }
          throw err;
        }
      }
      throw lastError;
    }

    // ==========================================
    // HEALTH CHECK & CONNECTION MONITORING
    // ==========================================

    async checkHealth() {
      this._notifyState('connecting');
      const startTime = performance.now();

      try {
        // Try versioned /api/v1/health first, then fall back to /api/health
        let data;
        try {
          data = await this.request('/api/v1/health', { timeout: 3500 });
        } catch (e) {
          data = await this.request('/api/health', { timeout: 3500 });
        }

        const latencyMs = Math.round(performance.now() - startTime);
        const healthResult = {
          ...data,
          latencyMs,
          checkedAt: new Date().toISOString()
        };

        this._notifyState('connected', healthResult);
        return { success: true, data: healthResult };
      } catch (err) {
        this._notifyState('disconnected', {
          error: err.message,
          checkedAt: new Date().toISOString()
        });
        return { success: false, error: err };
      }
    }

    // ==========================================
    // DASHBOARD ENDPOINT
    // ==========================================

    async getDashboardSummary() {
      return this.fetchWithRetry('/api/v1/dashboard', { timeout: 5000 });
    }

    // ==========================================
    // ASSESSMENTS ENDPOINTS
    // ==========================================

    async createAssessment(payload) {
      return this.request('/api/v1/assessments', {
        method: 'POST',
        body: JSON.stringify(payload),
        timeout: 8000
      });
    }

    async getAssessments(params = {}) {
      const searchParams = new URLSearchParams();
      if (params.type) searchParams.set('assessment_type', params.type);
      if (params.search) searchParams.set('search', params.search);
      const qs = searchParams.toString();
      const endpoint = `/api/v1/assessments${qs ? '?' + qs : ''}`;
      return this.fetchWithRetry(endpoint, { timeout: 5000 });
    }

    async getAssessmentById(assessmentId) {
      return this.fetchWithRetry(`/api/v1/assessments/${encodeURIComponent(assessmentId)}`, { timeout: 5000 });
    }

    async compareAssessments(id1, id2) {
      const qs = new URLSearchParams({ id1, id2 }).toString();
      return this.fetchWithRetry(`/api/v1/assessments/compare?${qs}`, { timeout: 6000 });
    }

    async deleteAssessment(assessmentId) {
      return this.request(`/api/v1/assessments/${encodeURIComponent(assessmentId)}`, {
        method: 'DELETE',
        timeout: 5000
      });
    }

    async purgeAllAssessments() {
      return this.request('/api/v1/assessments', {
        method: 'DELETE',
        timeout: 6000
      });
    }

    // ==========================================
    // SCAN REPORT ENDPOINTS
    // ==========================================

    async uploadReport(file) {
      const formData = new FormData();
      formData.append('file', file);
      return this.request('/api/v1/reports', {
        method: 'POST',
        body: formData,
        timeout: 25000 // Allow up to 25s for large OCR/PDF scans
      });
    }

    async verifyReport(reportId, verifiedFindings, options = {}) {
      return this.request(`/api/v1/reports/${encodeURIComponent(reportId)}/verify`, {
        method: 'POST',
        body: JSON.stringify({
          report_id: reportId,
          verified_findings: verifiedFindings,
          corrected_raw_text: options.correctedRawText || null,
          corrected_sections: options.correctedSections || null,
          notes: options.notes || (typeof options === 'string' ? options : '')
        }),
        timeout: 8000
      });
    }

    async getReportById(reportId) {
      return this.fetchWithRetry(`/api/v1/reports/${encodeURIComponent(reportId)}`, { timeout: 5000 });
    }

    // ==========================================
    // PHASE 8: AI REPORT UNDERSTANDING & EVIDENCE
    // ==========================================

    async explainReport(reportId) {
      return this.fetchWithRetry(`/api/v1/reports/${encodeURIComponent(reportId)}/explain`, { timeout: 8000 });
    }

    async searchReportEvidence(reportId, query) {
      return this.request(`/api/v1/reports/${encodeURIComponent(reportId)}/search-evidence`, {
        method: 'POST',
        body: JSON.stringify({ query }),
        timeout: 6000
      });
    }

    async checkClaim(claimOrQuestion, reportId = null, reportText = null) {
      return this.request('/api/v1/reports/check-claim', {
        method: 'POST',
        body: JSON.stringify({
          claim_or_question: claimOrQuestion,
          report_id: reportId,
          report_text: reportText
        }),
        timeout: 5000
      });
    }

    async getTermExplanation(term) {
      return this.fetchWithRetry(`/api/v1/reports/terms/${encodeURIComponent(term)}`, { timeout: 4000 });
    }

    // ==========================================
    // PHASE 11: AI EVALUATION & BENCHMARKING
    // ==========================================

    async getLatestBenchmarkReport() {
      return this.fetchWithRetry('/api/v1/evaluations/benchmark-latest', { timeout: 8000 });
    }

    async runBenchmark() {
      return this.request('/api/v1/evaluations/run-benchmark', {
        method: 'POST',
        timeout: 15000
      });
    }

    async getBenchmarkDatasetInfo() {
      return this.fetchWithRetry('/api/v1/evaluations/dataset-info', { timeout: 5000 });
    }

    // ==========================================
    // PHASE 18: EVIDENCE INTEGRITY & CORE INNOVATION
    // ==========================================

    async runEvidencePipeline(payload) {
      return this.request('/api/v1/evidence/pipeline', {
        method: 'POST',
        body: JSON.stringify(payload),
        timeout: 10000
      });
    }

    async getEvidenceDependencyGraph(reportData) {
      return this.request('/api/v1/evidence/dependency-graph', {
        method: 'POST',
        body: JSON.stringify(reportData),
        timeout: 6000
      });
    }

    async applyChangeImpact(payload) {
      return this.request('/api/v1/evidence/change-impact', {
        method: 'POST',
        body: JSON.stringify(payload),
        timeout: 8000
      });
    }

    async evaluateComparability(priorStudy, currentStudy) {
      return this.request('/api/v1/evidence/comparability-gate', {
        method: 'POST',
        body: JSON.stringify({ prior_study: priorStudy, current_study: currentStudy }),
        timeout: 6000
      });
    }

    async getActiveAcquisition(payload) {
      return this.request('/api/v1/evidence/active-acquisition', {
        method: 'POST',
        body: JSON.stringify(payload),
        timeout: 6000
      });
    }

    async sanitizePhi(text, documentId = 'DOC_UI') {
      return this.request('/api/v1/evidence/sanitize', {
        method: 'POST',
        body: JSON.stringify({ text, document_id: documentId }),
        timeout: 5000
      });
    }

    async getEvidenceBenchmark() {
      return this.fetchWithRetry('/api/v1/evidence/benchmark', { timeout: 12000 });
    }
  }

  // Attach singleton to window
  window.PathoGuardAPI = new PathoGuardApiClient();
})();
