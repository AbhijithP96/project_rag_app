// src/widget/widgetStyles.ts

export const WIDGET_STYLES = `

/* ── RESET ────────────────────────────────────────────── */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

button, input, textarea {
  font: inherit;
  border: none;
  outline: none;
  background: none;
  cursor: pointer;
}

ul, ol { list-style: none; }

/* ── THEME TOKENS — dark (default) ───────────────────── */
:host {
  --bg-primary:      #0d0d0f;
  --bg-secondary:    #141416;
  --bg-tertiary:     #1a1a1d;
  --bg-elevated:     #1f1f23;
  --bg-hover:        #25252a;

  --border:          #2a2a2f;
  --border-bright:   #3a3a42;

  --text-primary:    #e8e8ed;
  --text-secondary:  #8e8e99;
  --text-muted:      #5a5a66;

  --accent:          #4af0a4;
  --accent-dim:      #1a3d2e;
  --accent-text:     #0d2e1f;

  --error:           #f05050;
  --error-dim:       #2e1414;
  --warning:         #f0a050;
  --warning-dim:     #2e1e0a;
  --info:            #5090f0;
  --info-dim:        #0a1a2e;

  --font:            'Cascadia Code', 'JetBrains Mono', 'Fira Code',
                      ui-monospace, 'Courier New', monospace;

  --radius-sm:  4px;
  --radius:     6px;
  --radius-lg:  10px;
  --transition: 150ms ease;

  display: block;
  width: 100%;
  height: 100%;
  font-family: var(--font);
  font-size: 13px;
  color: var(--text-primary);
}

/* ── THEME TOKENS — light ─────────────────────────────── */
:host([data-theme="light"]) {
  --bg-primary:      #f5f5f7;
  --bg-secondary:    #ffffff;
  --bg-tertiary:     #ebebee;
  --bg-elevated:     #ffffff;
  --bg-hover:        #e2e2e8;

  --border:          #d8d8de;
  --border-bright:   #b8b8c2;

  --text-primary:    #1a1a1f;
  --text-secondary:  #6a6a78;
  --text-muted:      #9a9aa8;

  --accent:          #0a7c4a;
  --accent-dim:      #d4f0e4;
  --accent-text:     #ffffff;

  --error:           #c83232;
  --error-dim:       #fde8e8;
  --warning:         #c87820;
  --warning-dim:     #fdf0e0;
  --info:            #2860c8;
  --info-dim:        #e0eafd;
}

/* ── WIDGET SHELL ─────────────────────────────────────── */
.widget-shell {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  background: var(--bg-primary);
  overflow: hidden;
}

/* ── TOP BAR ──────────────────────────────────────────── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
}

.left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  letter-spacing: 0.03em;
}

.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* ── STATUS DOT ───────────────────────────────────────── */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  animation: pulse 2s ease-in-out infinite;
}

.status-dot.status-idle     { background: var(--text-muted); }
.status-dot.status-indexing { background: var(--warning); animation-duration: 0.6s; }
.status-dot.status-ready    { background: var(--accent); animation: none; opacity: 1; }
.status-dot.status-error    { background: var(--error);  animation: none; opacity: 1; }

/* ── PHASE LABEL ──────────────────────────────────────── */
.phase-label {
  font-size: 11px;
  color: var(--text-muted);
  letter-spacing: 0.04em;
  animation: fadeIn 0.2s ease;
}

/* ── THEME TOGGLE ─────────────────────────────────────── */
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius);
  color: var(--text-muted);
  font-size: 16px;
  line-height: 1;
  transition: color var(--transition), background var(--transition);
}

.theme-toggle:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.theme-toggle:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── INDEX MANAGER ────────────────────────────────────── */
.index-manager {
  flex-shrink: 0;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}

.index-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background var(--transition);
}

.index-header:hover { background: var(--bg-hover); }

.index-header-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.index-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.index-status-dot.status-idle     { background: var(--text-muted); }
.index-status-dot.status-indexing {
  background: var(--warning);
  animation: pulse 0.6s ease-in-out infinite;
}
.index-status-dot.status-ready    { background: var(--accent); }
.index-status-dot.status-error    { background: var(--error); }

.index-title {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.index-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.index-badge.ready {
  color: var(--accent);
  background: var(--accent-dim);
  border-color: var(--accent);
}

.index-badge.indexing {
  color: var(--warning);
  background: var(--warning-dim);
  border-color: var(--warning);
}

.index-badge.error {
  color: var(--error);
  background: var(--error-dim);
  border-color: var(--error);
}

.index-chevron {
  font-size: 10px;
  color: var(--text-muted);
}

.index-body {
  padding: 8px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  animation: fadeIn 0.15s ease;
  border-top: 1px solid var(--border);
}

/* ── PICKER AREA ──────────────────────────────────────── */
.index-picker-area {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.index-selected-dir {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.index-folder-icon {
  font-size: 12px;
  color: var(--accent);
  flex-shrink: 0;
}

.index-folder-name {
  font-size: 12px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.index-folder-ready {
  font-size: 10px;
  color: var(--accent);
  flex-shrink: 0;
}

.index-picker-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.index-pick-btn {
  flex: 1;
  height: 30px;
  padding: 0 10px;
  border-radius: var(--radius);
  border: 1px dashed var(--border-bright);
  background: var(--bg-primary);
  color: var(--text-secondary);
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: border-color var(--transition), color var(--transition);
  user-select: none;
}

.index-pick-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.index-pick-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  pointer-events: none;
}

.index-pick-icon { font-size: 14px; }

.index-fallback-toggle {
  font-size: 10px;
  color: var(--text-muted);
  cursor: pointer;
  align-self: flex-start;
  transition: color var(--transition);
  background: none;
  border: none;
  padding: 0;
}

.index-fallback-toggle:hover { color: var(--text-secondary); }

/* ── PATH INPUT ROW ───────────────────────────────────── */
.index-path-row {
  display: flex;
  gap: 6px;
}

.index-path-input {
  flex: 1;
  height: 30px;
  padding: 0 8px;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text-primary);
  font-size: 12px;
  transition: border-color var(--transition);
  caret-color: var(--accent);
}

.index-path-input:focus        { border-color: var(--border-bright); }
.index-path-input:disabled     { opacity: 0.5; }
.index-path-input::placeholder { color: var(--text-muted); }

/* ── SHARED BUTTONS ───────────────────────────────────── */
.index-btn {
  height: 30px;
  padding: 0 12px;
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--accent-text);
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: opacity var(--transition);
  cursor: pointer;
  border: none;
}

.index-btn:hover    { opacity: 0.85; }
.index-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.index-clear-btn {
  height: 30px;
  padding: 0 10px;
  font-size: 11px;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  transition: color var(--transition), border-color var(--transition);
  cursor: pointer;
  flex-shrink: 0;
  background: none;
}

.index-clear-btn:hover {
  color: var(--error);
  border-color: var(--error);
}

/* ── INDEX SPINNER ────────────────────────────────────── */
.index-spinner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
  display: inline-block;
}

/* ── PROGRESS ─────────────────────────────────────────── */
.index-progress {
  display: flex;
  flex-direction: column;
  gap: 5px;
  animation: fadeIn 0.2s ease;
}

.index-current-file {
  display: flex;
  gap: 6px;
  font-size: 11px;
  overflow: hidden;
}

.index-progress-label { color: var(--text-muted); flex-shrink: 0; }

.index-progress-value {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.index-progress-track {
  height: 2px;
  background: var(--border);
  border-radius: 1px;
  overflow: hidden;
}

.index-progress-fill {
  height: 100%;
  background: var(--warning);
  border-radius: 1px;
  transition: width 0.3s ease;
}

.index-progress-stats {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--text-muted);
}

/* ── FILE LIST ────────────────────────────────────────── */
.index-file-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  animation: fadeIn 0.2s ease;
}

.index-file-list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 2px;
}

.index-file-list-title {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.index-file-list-count {
  font-size: 10px;
  color: var(--accent);
}

.index-file-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 0;
}

.index-file-icon {
  font-size: 8px;
  color: var(--accent);
  flex-shrink: 0;
}

.index-file-name {
  flex: 1;
  font-size: 11px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.index-file-chunks {
  font-size: 10px;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* ── INDEX ERROR ──────────────────────────────────────── */
.index-error {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius);
  border: 1px solid var(--error);
  background: var(--error-dim);
  font-size: 12px;
  animation: fadeIn 0.2s ease;
}

.index-error-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.index-error-msg {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.index-error-hint {
  font-size: 10px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.index-retry-btn {
  font-size: 11px;
  color: var(--error);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--error);
  cursor: pointer;
  flex-shrink: 0;
  background: none;
  transition: background var(--transition);
}

.index-retry-btn:hover { background: var(--error-dim); }

/* ── DIRECTORY BROWSER ────────────────────────────────── */
.dir-browser {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-primary);
  overflow: hidden;
  animation: fadeIn 0.15s ease;
}

.dir-browser-path {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border);
  min-width: 0;
}

.dir-nav-btn {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  cursor: pointer;
  flex-shrink: 0;
  background: none;
  transition: color var(--transition), border-color var(--transition);
}

.dir-nav-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.dir-current-path {
  font-size: 10px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  direction: rtl;
  text-align: left;
  flex: 1;
  min-width: 0;
}

.dir-browser-list {
  max-height: 150px;
  overflow-y: auto;
  padding: 4px 0;
}

.dir-browser-empty {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  padding: 12px;
}

.dir-browser-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  transition: background var(--transition);
}

.dir-browser-item:hover { background: var(--bg-hover); }

.dir-item-navigate {
  font-size: 10px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px 4px;
  flex-shrink: 0;
  background: none;
  border: none;
  transition: color var(--transition);
}

.dir-item-navigate:hover { color: var(--accent); }

.dir-item-name {
  flex: 1;
  font-size: 11px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dir-item-select {
  font-size: 10px;
  color: var(--accent);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--accent);
  cursor: pointer;
  flex-shrink: 0;
  background: none;
  transition: background var(--transition);
}

.dir-item-select:hover { background: var(--accent-dim); }

.dir-browser-actions {
  display: flex;
  gap: 6px;
  padding: 6px 8px;
  border-top: 1px solid var(--border);
  background: var(--bg-tertiary);
}

/* ── MAIN AREA ────────────────────────────────────────── */
.main-area {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

.message-column {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.inspector-column {
  width: 260px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  overflow-y: auto;
  background: var(--bg-secondary);
  animation: slideIn 0.2s ease;
}

/* ── MESSAGE AREA ─────────────────────────────────────── */
.message-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  scroll-behavior: smooth;
  min-height: 0;
}

/* ── EMPTY STATE ──────────────────────────────────────── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background-image: radial-gradient(
    circle, var(--border) 1px, transparent 1px
  );
  background-size: 24px 24px;
  border-radius: var(--radius);
  padding: 40px;
  min-height: 200px;
}

.empty-title {
  font-size: 18px;
  font-weight: 500;
  color: var(--text-secondary);
  letter-spacing: 0.05em;
}

.empty-sub {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
}

/* ── PHASE INDICATOR ──────────────────────────────────── */
.phase-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  animation: fadeIn 0.2s ease;
  align-self: flex-start;
}

.phase-spinner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 1.5px solid var(--border-bright);
  border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

.phase-text {
  font-size: 12px;
  color: var(--text-secondary);
}

/* ── MESSAGE BUBBLES ──────────────────────────────────── */
.message-row {
  display: flex;
  animation: fadeIn 0.2s ease;
}

.message-row.user      { justify-content: flex-end; }
.message-row.assistant { justify-content: flex-start; }

.bubble {
  max-width: 85%;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 14px;
  border-radius: var(--radius-lg);
  position: relative;
}

.user-bubble {
  background: var(--accent-dim);
  border: 1px solid var(--accent);
  border-bottom-right-radius: var(--radius-sm);
}

.assistant-bubble {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-bottom-left-radius: var(--radius-sm);
}

.bubble-role {
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.assistant-bubble .bubble-role { color: var(--accent); }

.bubble-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.7;
  word-break: break-word;
}

.bubble-time {
  font-size: 10px;
  color: var(--text-muted);
  align-self: flex-end;
  margin-top: 2px;
}

.bubble-usage {
  display: flex;
  gap: 6px;
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 4px;
  flex-wrap: wrap;
}

/* ── MARKDOWN ─────────────────────────────────────────── */
.md-p            { margin: 0 0 8px; }
.md-p:last-child { margin-bottom: 0; }
.md-bold         { font-weight: 600; color: var(--text-primary); }
.md-italic       { font-style: italic; }
.md-link-blocked { color: var(--text-secondary); text-decoration: underline dotted; cursor: default; }

.md-code {
  font-family: var(--font);
  font-size: 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 1px 5px;
  color: var(--accent);
}

.md-codeblock {
  font-family: var(--font);
  font-size: 12px;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 12px;
  overflow-x: auto;
  margin: 8px 0;
  color: var(--text-primary);
  line-height: 1.6;
}

.md-ul, .md-ol { padding-left: 16px; margin: 6px 0; }
.md-li         { margin: 2px 0; font-size: 13px; color: var(--text-primary); }
.md-ul .md-li  { list-style: disc; }
.md-ol .md-li  { list-style: decimal; }

/* ── CURSOR ───────────────────────────────────────────── */
.cursor {
  display: inline-block;
  width: 2px;
  height: 14px;
  background: var(--accent);
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0; }
}

/* ── CITATION BADGE ───────────────────────────────────── */
.citation-wrapper { position: relative; display: inline; }

.citation-badge {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: var(--radius-sm);
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid var(--accent);
  cursor: pointer;
  margin: 0 1px;
  transition: background var(--transition);
  vertical-align: super;
  line-height: 1;
}

.citation-badge:hover,
.citation-badge.active  { background: var(--accent); color: var(--accent-text); }
.citation-badge.pending { opacity: 0.5; cursor: default; }
.citation-badge.missing { opacity: 0.3; cursor: default; }

/* ── CITATION POPOVER ─────────────────────────────────── */
.citation-popover {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 0;
  width: 280px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 10px 12px;
  z-index: 100;
  animation: fadeIn 0.15s ease;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

.popover-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.popover-source {
  font-size: 11px;
  font-weight: 500;
  color: var(--accent);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.popover-page  { font-size: 10px; color: var(--text-muted); }

.popover-close {
  font-size: 10px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 2px 4px;
  border-radius: var(--radius-sm);
  transition: color var(--transition), background var(--transition);
}

.popover-close:hover {
  color: var(--text-primary);
  background: var(--bg-hover);
}

.popover-scores {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 8px;
}

.popover-text {
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.6;
  border-top: 1px solid var(--border);
  padding-top: 8px;
  max-height: 80px;
  overflow-y: auto;
}

/* ── SCORE BARS ───────────────────────────────────────── */
.score-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-label {
  font-size: 10px;
  color: var(--text-muted);
  width: 52px;
  flex-shrink: 0;
}

.score-track,
.score-bar-track {
  flex: 1;
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.score-fill,
.score-bar-fill            { height: 100%; border-radius: 2px; background: var(--accent); transition: width 0.4s ease; }
.score-fill.bm25,
.score-bar-fill.bm25       { background: var(--info); }
.score-fill.vector,
.score-bar-fill.vector     { background: var(--warning); }

.score-value {
  font-size: 10px;
  color: var(--text-muted);
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}

/* ── TOKEN BUDGET ─────────────────────────────────────── */
.token-budget {
  padding: 8px 12px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.budget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.budget-title {
  font-size: 10px;
  color: var(--text-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.budget-percent {
  font-size: 11px;
  font-weight: 500;
  transition: color 0.3s ease;
}

.budget-track {
  height: 3px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 6px;
}

.budget-bar {
  height: 100%;
  width: var(--bar-width, 0%);
  background: var(--bar-color, var(--accent));
  border-radius: 2px;
  transition: width 0.4s ease, background 0.3s ease;
}

.budget-bar.streaming { animation: budget-pulse 1.5s ease-in-out infinite; }

@keyframes budget-pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.6; }
}

.budget-breakdown {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.budget-item        { display: flex; align-items: center; gap: 3px; }
.budget-item-label  { font-size: 10px; color: var(--text-muted); }
.budget-item-value  { font-size: 10px; color: var(--text-secondary); }
.budget-item-value.total { font-weight: 500; }
.budget-divider     { font-size: 10px; color: var(--border-bright); }

.budget-warning {
  margin-top: 4px;
  font-size: 11px;
  color: var(--error);
  animation: fadeIn 0.2s ease;
}

/* ── CONTEXT INSPECTOR ────────────────────────────────── */
.inspector {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.inspector-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  user-select: none;
  transition: background var(--transition);
  flex-shrink: 0;
}

.inspector-header:hover { background: var(--bg-hover); }

.inspector-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.inspector-title {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-secondary);
}

.inspector-count {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border: 1px solid var(--border);
}

.inspector-spinner {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid var(--border-bright);
  border-top-color: var(--accent);
  animation: spin 0.8s linear infinite;
}

.inspector-chevron { font-size: 10px; color: var(--text-muted); }

.inspector-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.inspector-empty {
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  padding: 20px 0;
}

/* ── CHUNK CARDS ──────────────────────────────────────── */
.chunk-card {
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  animation: fadeIn 0.2s ease;
}

.chunk-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  cursor: pointer;
  transition: background var(--transition);
}

.chunk-header:hover { background: var(--bg-hover); }

.chunk-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.chunk-index  { font-size: 10px; color: var(--accent); flex-shrink: 0; }
.chunk-source { font-size: 11px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chunk-page   { font-size: 10px; color: var(--text-muted); flex-shrink: 0; }
.chunk-chevron { font-size: 10px; color: var(--text-muted); flex-shrink: 0; }

.chunk-scores {
  padding: 4px 8px 6px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
}

.chunk-text {
  padding: 8px;
  font-size: 11px;
  color: var(--text-secondary);
  line-height: 1.6;
  border-top: 1px solid var(--border);
  max-height: 100px;
  overflow-y: auto;
}

/* ── ERROR CARD ───────────────────────────────────────── */
.error-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--error);
  background: var(--error-dim);
  animation: fadeIn 0.2s ease;
  margin-top: 6px;
}

.error-card.rerank_error {
  border-color: var(--warning);
  background: var(--warning-dim);
}

.error-icon { font-size: 12px; color: var(--error); flex-shrink: 0; margin-top: 2px; }
.error-card.rerank_error .error-icon { color: var(--warning); }

.error-body { display: flex; flex-direction: column; gap: 2px; flex: 1; }

.error-type { font-size: 12px; font-weight: 500; color: var(--error); }
.error-card.rerank_error .error-type { color: var(--warning); }

.error-msg { font-size: 12px; color: var(--text-secondary); }

.error-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: var(--warning-dim);
  color: var(--warning);
  border: 1px solid var(--warning);
  flex-shrink: 0;
  align-self: center;
}

/* ── INPUT BAR ────────────────────────────────────────── */
.input-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border);
  flex-shrink: 0;
}

.query-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text-primary);
  font-size: 13px;
  transition: border-color var(--transition);
  caret-color: var(--accent);
}

.query-input::placeholder { color: var(--text-muted); }
.query-input:focus        { border-color: var(--border-bright); outline: none; }
.query-input:disabled     { opacity: 0.5; cursor: not-allowed; }

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--accent-text);
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: opacity var(--transition), background var(--transition);
  border: none;
  cursor: pointer;
}

.send-btn:hover    { opacity: 0.85; }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.send-btn.streaming {
  background: var(--bg-elevated);
  color: var(--error);
  border: 1px solid var(--error);
}

/* ── LOG DRAWER ───────────────────────────────────────── */
.log-drawer {
  flex-shrink: 0;
  border-top: 1px solid var(--border);
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  max-height: 28px;
  transition: max-height 0.25s ease;
  overflow: hidden;
}

.log-drawer.open { max-height: 220px; }

.log-handle {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 28px;
  padding: 0 12px;
  cursor: pointer;
  flex-shrink: 0;
  user-select: none;
  transition: background var(--transition);
}

.log-handle:hover { background: var(--bg-hover); }

.log-handle-bar {
  width: 24px;
  height: 2px;
  background: var(--border-bright);
  border-radius: 1px;
  flex-shrink: 0;
}

.log-handle-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.log-handle-title {
  font-size: 10px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.log-entry-count {
  font-size: 10px;
  color: var(--text-muted);
  padding: 1px 5px;
background: var(--bg-tertiary);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}

.log-handle-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.log-clear-btn {
  font-size: 10px;
  color: var(--text-muted);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  transition: color var(--transition), border-color var(--transition);
  cursor: pointer;
  background: none;
}

.log-clear-btn:hover {
  color: var(--error);
  border-color: var(--error);
}

.log-chevron { font-size: 10px; color: var(--text-muted); }

.log-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.log-empty {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  padding: 12px;
}

.log-entry {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 2px 12px;
  font-size: 11px;
  line-height: 1.6;
  transition: background var(--transition);
}

.log-entry:hover { background: var(--bg-hover); }

.log-time     { color: var(--text-muted); flex-shrink: 0; font-size: 10px; }

.log-level    { flex-shrink: 0; font-size: 10px; font-weight: 500; width: 36px; }
.log-level.level-info  { color: var(--accent); }
.log-level.level-warn  { color: var(--warning); }
.log-level.level-error { color: var(--error); }
.log-level.level-debug { color: var(--text-muted); }

.log-category { color: var(--info); flex-shrink: 0; width: 64px; font-size: 10px; }

.log-msg {
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── STATUS BAR ───────────────────────────────────────── */
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 28px;
  padding: 0 16px;
  flex-shrink: 0;
  background: var(--bg-tertiary);
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-muted);
}

.log-toggle-btn {
  font-size: 11px;
  color: var(--text-muted);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  transition: color var(--transition), border-color var(--transition);
  cursor: pointer;
  background: none;
}

.log-toggle-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.api-base {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  direction: rtl;
  text-align: left;
}

/* ── ANIMATIONS ───────────────────────────────────────── */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.35; }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-6px); }
  to   { opacity: 1; transform: translateX(0); }
}
`