async function validateForm() {
  const form = document.getElementById('job-form');
  const preset = document.getElementById('preset').value;
  
  // Check HTML5 validation
  if (!form.checkValidity()) {
    form.reportValidity();
    return false;
  }

  // Additional validation for required fields based on preset
  if (preset === 'video_processor' || preset === 'transcribe_processor') {
    const inputKey = document.getElementById('input_key').value.trim();
    const outputKey = document.getElementById('output_key').value.trim();
    if (!inputKey || !outputKey) {
      alert('Input Key and Output Key are required for this preset');
      return false;
    }
  }

  if (preset === 'download_processor') {
    const sourceUrl = document.getElementById('source_url').value.trim();
    const outputKey = document.getElementById('output_key').value.trim();
    if (!sourceUrl || !outputKey) {
      alert('Source URL and Output Key are required for this preset');
      return false;
    }
  }

  if (preset === 'scoring_processor') {
    const inputKey = document.getElementById('input_key').value.trim();
    const outputKey = document.getElementById('output_key').value.trim();
    const llmProvider = document.getElementById('llm_provider').value.trim();
    const llmModel = document.getElementById('llm_model').value.trim();
    if (!inputKey || !outputKey || !llmProvider || !llmModel) {
      alert('Input Key, Output Key, LLM Provider, and LLM Model are required for this preset');
      return false;
    }
  }

  return true;
}

async function postForm(path) {
  if (!validateForm()) {
    return;
  }

  const form = document.getElementById('job-form');
  const formData = new FormData(form);
  const obj = {};
  for (const [k, v] of formData.entries()) { obj[k] = v; }

  const resp = await fetch(path, { method: 'POST', body: new URLSearchParams(obj) });
  const json = await resp.json();
  document.getElementById('output').textContent = JSON.stringify(json, null, 2);
}

async function loadHistory() {
  try {
    const resp = await fetch('/history');
    const json = await resp.json();
    let history = json.history || [];
    
    if (history.length === 0) {
      document.getElementById('history-container').innerHTML = '<p class="text-muted">No jobs found in history.</p>';
      return;
    }
    
    // Sort by timestamp, latest first
    history.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    let html = '<div class="list-group list-group-flush">';
    history.forEach((job, index) => {
      const originalIndex = index;
      const timestamp = new Date(job.timestamp).toLocaleString();
      
      // Smart field selection: use form_data for original inputs, payload for derived values
      const operation = job.form_data?.operation || job.operation || 'custom';
      const computeType = job.form_data?.compute_type || job.payload?.data?.compute_type || job.compute_type || 'unknown';
      const scriptKey = job.form_data?.script_key || job.payload?.data?.script_key || job.script_key || 'unknown';
      const inputKey = job.form_data?.input_key || job.input_key || 'N/A';
      const outputKey = job.form_data?.output_key || job.output_key || 'N/A';
      const inputBucket = job.form_data?.input_bucket || job.input_bucket || 'N/A';
      const outputBucket = job.form_data?.output_bucket || job.output_bucket || 'N/A';
      const modelBucket = job.form_data?.model_bucket || job.model_bucket || 'N/A';
      const sourceUrl = job.form_data?.source_url || job.payload?.data?.args?.source_url || 'N/A';
      
      const status = job.status || 'unknown';
      const statusClass = status === 'success' ? 'success' : status === 'failed' ? 'failed' : '';
      const statusBadge = status === 'success' 
        ? '<span class="badge bg-success">Success</span>' 
        : status === 'failed'
        ? '<span class="badge bg-danger">Failed</span>'
        : '<span class="badge bg-secondary">Unknown</span>';
      
      html += `
        <div class="list-group-item history-item ${statusClass}">
          <div class="history-header">
            <div>
              <h6 class="mb-0 fw-bold">${operation}</h6>
              <small class="text-muted">${computeType}</small>
            </div>
            <div class="history-badge-group">
              ${statusBadge}
              <button class="badge bg-info border-0" type="button" data-logs-timestamp="${job.timestamp}">Logs</button>
              <button class="badge bg-danger border-0" type="button" data-delete-timestamp="${job.timestamp}">Delete</button>
            </div>
          </div>

          <div class="history-row">
            <div>
              <div class="history-section-label">Input</div>
              <div class="history-section-value">${inputKey}</div>
              ${inputBucket !== 'N/A' ? `<div class="history-section-value muted">${inputBucket}</div>` : ''}
            </div>
            <div>
              <div class="history-section-label">Output</div>
              <div class="history-section-value">${outputKey}</div>
              ${outputBucket !== 'N/A' ? `<div class="history-section-value muted">${outputBucket}</div>` : ''}
            </div>
          </div>

          ${sourceUrl !== 'N/A' ? `<div class="history-section" style="margin-top: 0.3rem;"><small class="text-muted">Source: ${sourceUrl}</small></div>` : ''}

          ${scriptKey !== 'unknown' ? `<div class="history-section" style="margin-top: 0.3rem;"><small class="text-muted">Script: ${scriptKey}</small></div>` : ''}
          ${modelBucket !== 'N/A' ? `<div class="history-section"><small class="text-muted">Model: ${modelBucket}</small></div>` : ''}
          ${job.error ? `<div class="history-error-box"><small><strong>Error:</strong> ${job.error}</small></div>` : ''}

          <div class="history-meta">
            <div class="history-timestamp">
              <small>${timestamp}</small>
              ${job.sns_message_id ? `<br><small>ID: ${job.sns_message_id.slice(-8)}</small>` : ''}
            </div>
          </div>
        </div>
      `;
    });
    html += '</div>';
    
    document.getElementById('history-container').innerHTML = html;

    document.querySelectorAll('[data-delete-timestamp]').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const timestamp = e.currentTarget.getAttribute('data-delete-timestamp');
        await deleteHistoryEntry(timestamp);
      });
    });

    document.querySelectorAll('[data-logs-timestamp]').forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        const timestamp = e.currentTarget.getAttribute('data-logs-timestamp');
        await tailLogs(timestamp);
      });
    });
  } catch (error) {
    document.getElementById('history-container').innerHTML = '<p class="text-danger">Error loading history: ' + error.message + '</p>';
  }
}

async function deleteHistoryEntry(timestamp) {
  if (!confirm('Delete this history entry?')) {
    return;
  }

  try {
    const form = new URLSearchParams({ timestamp });
    const resp = await fetch('/history/delete', { method: 'POST', body: form });
    const json = await resp.json();
    document.getElementById('output').textContent = JSON.stringify(json, null, 2);
    await loadHistory();
  } catch (error) {
    document.getElementById('output').textContent = JSON.stringify({ error: error.message }, null, 2);
  }
}

async function tailLogs(timestamp) {
  try {
    const form = new URLSearchParams({ timestamp });
    const resp = await fetch('/logs/tail', { method: 'POST', body: form });
    const json = await resp.json();
    
    if (json.error) {
      document.getElementById('output').textContent = JSON.stringify({ error: json.error }, null, 2);
    } else {
      const logs = json.logs || [];
      const formatted = logs.length > 0 
        ? logs.join('\n')
        : json.message || 'No logs found';
      document.getElementById('output').textContent = formatted;
    }
  } catch (error) {
    document.getElementById('output').textContent = JSON.stringify({ error: error.message }, null, 2);
  }
}

function updatePresetFields() {
  const preset = document.getElementById('preset').value;
  const allFields = document.querySelectorAll('.preset-field');
  
  allFields.forEach(field => {
    const presets = field.getAttribute('data-presets');
    if (!presets) {
      field.classList.add('active');
      // Enable required fields in always-visible sections
      field.querySelectorAll('[required]').forEach(input => {
        input.disabled = false;
      });
      return;
    }
    
    const presetList = presets.split(',');
    if (preset && presetList.includes(preset)) {
      field.classList.add('active');
      // Enable required fields when section is active
      field.querySelectorAll('[required]').forEach(input => {
        input.disabled = false;
      });
    } else {
      field.classList.remove('active');
      // Disable required fields when section is hidden to skip HTML5 validation
      field.querySelectorAll('[required]').forEach(input => {
        input.disabled = true;
        input.value = '';
      });
    }
  });
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', () => {
  updatePresetFields();
  document.getElementById('preset').addEventListener('change', updatePresetFields);
  
  document.getElementById('preview-btn').addEventListener('click', (e) => postForm('/preview'));
  document.getElementById('publish-btn').addEventListener('click', (e) => postForm('/publish'));
  
  document.getElementById('expand-output-btn').addEventListener('click', (e) => {
    const container = document.getElementById('output-container');
    container.classList.toggle('fullscreen');
    const btn = e.currentTarget;
    btn.textContent = container.classList.contains('fullscreen') ? '⛶ (Press Esc)' : '⛶';
  });
  
  document.getElementById('expand-history-btn').addEventListener('click', (e) => {
    const container = document.getElementById('history-container-wrapper');
    container.classList.toggle('fullscreen');
    const btn = e.currentTarget;
    btn.textContent = container.classList.contains('fullscreen') ? '⛶ (Press Esc)' : '⛶';
  });
  
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const outputContainer = document.getElementById('output-container');
      const historyContainer = document.getElementById('history-container-wrapper');
      
      if (outputContainer.classList.contains('fullscreen')) {
        outputContainer.classList.remove('fullscreen');
        document.getElementById('expand-output-btn').textContent = '⛶';
      }
      
      if (historyContainer.classList.contains('fullscreen')) {
        historyContainer.classList.remove('fullscreen');
        document.getElementById('expand-history-btn').textContent = '⛶';
      }
    }
  });
  
  loadHistory();
});
