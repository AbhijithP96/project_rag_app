// src/components/IndexManager.tsx
import { useState, useRef } from 'react'
import { mockIndexDirectory } from '../api/mockapi'
import { logger } from '../utils/logger'
import type { IndexProgressEvent } from '../api/types'

const API_BASE = 'http://localhost:8000'

interface Props {
  onStatusChange: (status: 'idle' | 'indexing' | 'ready' | 'error') => void
}

interface IndexState {
  status:         'idle' | 'indexing' | 'ready' | 'error'
  filesProcessed: string[]
  chunksIndexed:  number
  currentFile:    string
  errorMsg:       string
  selectedDir:    string
}

interface DirEntry {
  name: string
  path: string
}

const initial: IndexState = {
  status:         'idle',
  filesProcessed: [],
  chunksIndexed:  0,
  currentFile:    '',
  errorMsg:       '',
  selectedDir:    '',
}

export function IndexManager({ onStatusChange }: Props) {
  const [open,        setOpen]       = useState(false)
  const [indexState,  setIndexState] = useState<IndexState>(initial)
  const [manualPath,  setManualPath] = useState('')
  const [showManual,  setShowManual] = useState(false)

  const [browserOpen,    setBrowserOpen]    = useState(false)
  const [browserPath,    setBrowserPath]    = useState('')
  const [browserDirs,    setBrowserDirs]    = useState<DirEntry[]>([])
  const [browserLoading, setBrowserLoading] = useState(false)

  const abortRef = useRef(false)

  const {
    status, filesProcessed, chunksIndexed,
    currentFile, errorMsg, selectedDir,
  } = indexState

  // ── directory browser ─────────────────────────────
  const openBrowser = async () => {
    setBrowserLoading(true)
    try {
      const res  = await fetch(`${API_BASE}/directories`)
      const data = await res.json()
      setBrowserPath(data.current)
      setBrowserDirs(data.dirs)
      setBrowserOpen(true)
    } catch (e) {
      logger.error('index', 'failed to load directories')
    } finally {
      setBrowserLoading(false)
    }
  }

  const navigateTo = async (path: string) => {
    setBrowserLoading(true)
    try {
      const res  = await fetch(
        `${API_BASE}/directories?path=${encodeURIComponent(path)}`
      )
      const data = await res.json()
      setBrowserPath(data.current)
      setBrowserDirs(data.dirs)
    } catch (e) {
      logger.error('index', `failed to navigate to ${path}`)
    } finally {
      setBrowserLoading(false)
    }
  }

  const navigateUp = () => {
    const parent = browserPath.split('/').slice(0, -1).join('/') || '/'
    navigateTo(parent)
  }

  const selectAndIndex = (dirPath: string, dirName: string) => {
    setIndexState(prev => ({ ...prev, selectedDir: dirName }))
    setManualPath(dirPath)
    setBrowserOpen(false)
    runIndex(dirPath)
  }

  const handleRetryBrowse = () => {
    setBrowserOpen(false)
    openBrowser()
  }

  // ── shared index runner ───────────────────────────
  const runIndex = async (path: string) => {
    abortRef.current = false

    setIndexState(prev => ({
      ...prev,
      status:         'indexing',
      filesProcessed: [],
      chunksIndexed:  0,
      currentFile:    '',
      errorMsg:       '',
      selectedDir:    prev.selectedDir || path,
    }))
    onStatusChange('indexing')
    logger.info('index', `indexing: ${path}`)

    try {
      const generator = mockIndexDirectory({ directory: path })
      for await (const event of generator) {
        if (abortRef.current) break
        handleProgressEvent(event)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setIndexState(prev => ({ ...prev, status: 'error', errorMsg: msg }))
      onStatusChange('error')
      logger.error('index', `failed: ${msg}`)
    }
  }

  const handleProgressEvent = (event: IndexProgressEvent) => {
    setIndexState(prev => ({
      ...prev,
      status:         event.status === 'complete' ? 'ready' : event.status,
      filesProcessed: event.filesProcessed,
      chunksIndexed:  event.chunksIndexed,
      currentFile:    event.currentFile ?? '',
      errorMsg:       event.message ?? '',
    }))

    if (event.status === 'complete') {
      onStatusChange('ready')
      logger.info('index',
        `complete · ${event.filesProcessed.length} files · ${event.chunksIndexed} chunks`
      )
    }

    if (event.status === 'error') {
      onStatusChange('error')
      logger.error('index', event.message ?? 'index error')
    }

    if (event.currentFile) {
      logger.info('index', `processing: ${event.currentFile}`)
    }
  }

  const handleReset = () => {
    abortRef.current = true
    setIndexState(initial)
    setManualPath('')
    setBrowserOpen(false)
    onStatusChange('idle')
    logger.info('index', 'index cleared')
  }

  return (
    <div className="index-manager">

      {/* ── HEADER ── */}
      <div
        className="index-header"
        onClick={() => setOpen(prev => !prev)}
        role="button"
        aria-expanded={open}
      >
        <div className="index-header-left">
          <span className={`index-status-dot status-${status}`} />
          <span className="index-title">index manager</span>
          {status === 'ready' && (
            <span className="index-badge ready">
              {filesProcessed.length} files · {chunksIndexed} chunks
            </span>
          )}
          {status === 'indexing' && (
            <span className="index-badge indexing">
              <span className="index-spinner" />
              indexing...
            </span>
          )}
          {status === 'error' && (
            <span className="index-badge error">error</span>
          )}
        </div>
        <span className="index-chevron">{open ? '▾' : '▸'}</span>
      </div>

      {/* ── BODY ── */}
      {open && (
        <div className="index-body">

          {/* ── IDLE / READY ── */}
          {(status === 'idle' || status === 'ready') && (
            <div className="index-picker-area">

              {selectedDir && (
                <div className="index-selected-dir">
                  <span className="index-folder-icon">◈</span>
                  <span className="index-folder-name">{selectedDir}</span>
                  <span className="index-folder-ready">
                    {status === 'ready' ? '· indexed' : ''}
                  </span>
                </div>
              )}

              {/* ── DIRECTORY BROWSER ── */}
              {browserOpen ? (
                <div className="dir-browser">

                  <div className="dir-browser-path">
                    <button
                      className="dir-nav-btn"
                      onClick={navigateUp}
                      title="Go up"
                    >
                      ↑
                    </button>
                    <span className="dir-current-path">{browserPath}</span>
                    {browserLoading && (
                      <span
                        className="index-spinner"
                        style={{ marginLeft: 'auto', flexShrink: 0 }}
                      />
                    )}
                  </div>

                  <div className="dir-browser-list">
                    {browserDirs.length === 0 && !browserLoading && (
                      <p className="dir-browser-empty">
                        no subdirectories — index this folder
                      </p>
                    )}
                    {browserDirs.map(dir => (
                      <div key={dir.path} className="dir-browser-item">
                        <button
                          className="dir-item-navigate"
                          onClick={() => navigateTo(dir.path)}
                          title="Open folder"
                        >
                          ▸
                        </button>
                        <span className="dir-item-name">{dir.name}</span>
                        <button
                          className="dir-item-select"
                          onClick={() => selectAndIndex(dir.path, dir.name)}
                        >
                          index
                        </button>
                      </div>
                    ))}
                  </div>

                  <div className="dir-browser-actions">
                    <button
                      className="index-btn"
                      onClick={() => selectAndIndex(
                        browserPath,
                        browserPath.split('/').pop() ?? browserPath,
                      )}
                    >
                      index this folder
                    </button>
                    <button
                      className="index-clear-btn"
                      onClick={() => setBrowserOpen(false)}
                    >
                      cancel
                    </button>
                  </div>

                </div>
              ) : (
                <div className="index-picker-row">
                  <button
                    className="index-pick-btn"
                    onClick={openBrowser}
                    disabled={browserLoading}
                  >
                    <span className="index-pick-icon">⊕</span>
                    {selectedDir ? 'change folder' : 'browse & select folder'}
                  </button>

                  {status === 'ready' && (
                    <button
                      className="index-btn"
                      onClick={() => runIndex(manualPath)}
                    >
                      re-index
                    </button>
                  )}

                  {status === 'ready' && (
                    <button
                      className="index-clear-btn"
                      onClick={handleReset}
                    >
                      clear
                    </button>
                  )}
                </div>
              )}

              <button
                className="index-fallback-toggle"
                onClick={() => setShowManual(p => !p)}
              >
                {showManual ? '▾' : '▸'} use path instead
              </button>

              {showManual && (
                <div className="index-path-row">
                  <input
                    className="index-path-input"
                    type="text"
                    value={manualPath}
                    onChange={e => setManualPath(e.target.value)}
                    placeholder="/full/path/to/docs"
                    spellCheck={false}
                  />
                  <button
                    className="index-btn"
                    onClick={() => {
                      const name = manualPath.split('/').pop() ?? manualPath
                      setIndexState(prev => ({ ...prev, selectedDir: name }))
                      runIndex(manualPath)
                    }}
                    disabled={!manualPath.trim()}
                  >
                    index
                  </button>
                </div>
              )}

            </div>
          )}

          {/* ── INDEXING — progress ── */}
          {status === 'indexing' && (
            <div className="index-progress">
              <div className="index-current-file">
                <span className="index-progress-label">processing</span>
                <span className="index-progress-value">{currentFile}</span>
              </div>
              <div className="index-progress-track">
                <div
                  className="index-progress-fill"
                  style={{
                    width: `${Math.min(100,
                      (filesProcessed.length / Math.max(filesProcessed.length, 1)) * 100
                    )}%`,
                  }}
                />
              </div>
              <div className="index-progress-stats">
                <span>{filesProcessed.length} files processed</span>
                <span>{chunksIndexed} chunks indexed</span>
              </div>
            </div>
          )}

          {/* ── READY — file list ── */}
          {status === 'ready' && filesProcessed.length > 0 && (
            <div className="index-file-list">
              <div className="index-file-list-header">
                <span className="index-file-list-title">indexed files</span>
                <span className="index-file-list-count">
                  {chunksIndexed} total chunks
                </span>
              </div>
              {filesProcessed.map(file => (
                <div key={file} className="index-file-row">
                  <span className="index-file-icon">◆</span>
                  <span className="index-file-name">{file}</span>
                  <span className="index-file-chunks">
                    ~{Math.floor(chunksIndexed / Math.max(filesProcessed.length, 1))}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* ── ERROR ── */}
          {status === 'error' && (
            <div className="index-error">
              <span className="error-icon">✕</span>
              <div className="index-error-body">
                <span className="index-error-msg">
                  {errorMsg?.split('\n')[0] || 'Indexing failed'}
                </span>
                {errorMsg?.includes('Available') && (
                  <span className="index-error-hint">
                    {errorMsg.split('\n').slice(2).join(' ')}
                  </span>
                )}
              </div>
              <button
                className="index-retry-btn"
                onClick={handleRetryBrowse}
              >
                browse
              </button>
            </div>
          )}

        </div>
      )}

    </div>
  )
}