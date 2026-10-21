/**
 * Automated Test for Frontend API Connection Layer (api.js)
 * Executes against live running FastAPI server on http://127.0.0.1:8000
 */

const fs = require('fs');
const path = require('path');

// Mock browser globals needed by api.js
global.window = {};
global.localStorage = {
  store: {},
  getItem(k) { return this.store[k] || null; },
  setItem(k, v) { this.store[k] = String(v); },
  removeItem(k) { delete this.store[k]; }
};

// Load api.js into memory
const apiCode = fs.readFileSync(path.join(__dirname, '..', '..', 'PathoGuard-AI-Frontend', 'api.js'), 'utf8');
eval(apiCode);

const api = global.window.PathoGuardAPI;

function logTest(name, passed, detail = '') {
  const sym = passed ? 'PASS' : 'FAIL';
  console.log(`[${sym}] ${name} ${detail ? '- ' + detail : ''}`);
  if (!passed) {
    throw new Error(`Test failed: ${name} - ${detail}`);
  }
}

async function runApiTests() {
  console.log('\n================ FRONTEND API CLIENT TEST SUITE ================');
  
  // 1. Verify instance initialization
  logTest('Client Instantiation', !!api, `Base URL: ${api.getBaseUrl()}`);

  // 2. State change listener test
  let lastReportedState = null;
  api.onConnectionChange((state, details) => {
    lastReportedState = state;
  });

  // 3. Health check
  const healthRes = await api.checkHealth();
  logTest(
    'api.checkHealth()',
    healthRes.success && lastReportedState === 'connected',
    `Status: ${healthRes.data?.status}, Latency: ${healthRes.data?.latencyMs}ms`
  );

  // 4. Dashboard Summary
  const dashRes = await api.getDashboardSummary();
  logTest(
    'api.getDashboardSummary()',
    dashRes.status === 'success' && dashRes.metrics !== undefined,
    `Total assessments: ${dashRes.metrics.total_assessments}, Recent items: ${dashRes.recent_assessments.length}`
  );

  // 5. Assessment Creation
  const newAssessmentPayload = {
    primary_symptoms: ['Persistent dry cough', 'Mild dyspnea'],
    onset: '3-6 weeks',
    trajectory: 'Worsening',
    frequency: 'Constant',
    age_bracket: '45-54',
    medical_history: ['None reported'],
    patient_note: 'Verified via frontend integration test'
  };

  const createdAsm = await api.createAssessment(newAssessmentPayload);
  logTest(
    'api.createAssessment()',
    createdAsm.status === 'Assessment summary ready' && !!createdAsm.assessment_id,
    `ID: ${createdAsm.assessment_id}, Suggested steps: ${createdAsm.suggested_next_steps.length}`
  );

  // 6. Get Assessments List
  const listRes = await api.getAssessments();
  logTest(
    'api.getAssessments()',
    listRes.total_count >= 1 && Array.isArray(listRes.items),
    `Count: ${listRes.total_count}`
  );

  // 7. Get Assessment by ID
  const singleAsm = await api.getAssessmentById(createdAsm.assessment_id);
  logTest(
    'api.getAssessmentById()',
    singleAsm.assessment_id === createdAsm.assessment_id,
    `Retrieved ID: ${singleAsm.assessment_id}`
  );

  // 8. Offline resilience & error handling test
  // Set invalid base URL and test graceful disconnection
  api.setBaseUrl('http://127.0.0.1:9999'); // Non-existent port
  const offlineHealth = await api.checkHealth();
  logTest(
    'Offline Handling & Disconnected State Transition',
    offlineHealth.success === false && lastReportedState === 'disconnected',
    `Reported State: ${lastReportedState}`
  );

  // Restore working base URL
  api.setBaseUrl('http://127.0.0.1:8000');
  const restoredHealth = await api.checkHealth();
  logTest(
    'Reconnection & Restored Health State',
    restoredHealth.success === true && lastReportedState === 'connected',
    `Restored Latency: ${restoredHealth.data?.latencyMs}ms`
  );

  // 9. Phase 18 Evidence Comparability Gate
  const compRes = await api.evaluateComparability(
    { text: 'CT chest reveals 2.0 cm nodule' },
    { text: 'Ultrasound liver reveals 3.0 cm cyst' }
  );
  logTest(
    'api.evaluateComparability()',
    compRes.decision === 'BLOCKED' && compRes.status === 'INCOMPATIBLE_ANATOMICAL_SITE',
    `Decision: ${compRes.decision}, Status: ${compRes.status}`
  );

  // 10. Phase 18 Privacy PHI Sanitization
  const sanRes = await api.sanitizePhi('Patient Name: Jane Doe, MRN: 998234. Normal scan.', 'TEST_CLIENT');
  logTest(
    'api.sanitizePhi()',
    sanRes.is_clean === true && sanRes.redacted_count >= 2,
    `Redacted count: ${sanRes.redacted_count}, Risk score: ${sanRes.leakage_risk_score}`
  );

  // 11. Phase 18 Live Evidence Benchmark Retrieval
  const benchRes = await api.getEvidenceBenchmark();
  logTest(
    'api.getEvidenceBenchmark()',
    benchRes.benchmark_id === 'EVAL-PHASE18-EVIDENCE-INTEGRITY' && benchRes.summary.status === 'ALL_HYPOTHESES_VALIDATED',
    `Status: ${benchRes.summary.status}, Duration: ${benchRes.summary.execution_duration_ms}ms`
  );

  console.log('================================================================\n');
}

runApiTests().catch((err) => {
  console.error('Test execution error:', err);
  process.exit(1);
});
