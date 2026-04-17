import { useEffect, useMemo, useRef, useState } from 'react'
import { getFetchLog } from '../api'

export default function FetchProgress({ onClose }) {
  const [lines, setLines] = useState([])
  const [running, setRunning] = useState(true)
  const [expanded, setExpanded] = useState(false)
  const bottomRef = useRef(null)
  const intervalRef = useRef(null)

  // Parse the last [N/M] occurrence in the log for progress
  const progress = useMemo(() => {
    for (let i = lines.length - 1; i >= 0; i--) {
      const m = lines[i].match(/\[(\d+)\/(\d+)\]/)
      if (m) return { current: parseInt(m[1]), total: parseInt(m[2]) }
    }
    return null
  }, [lines])

  const pct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : null

  const poll = async () => {
    try {
      const { data } = await getFetchLog()
      setLines(data.lines)
      setRunning(data.running)
      if (!data.running) clearInterval(intervalRef.current)
    } catch {
      // backend may be momentarily unavailable; keep trying
    }
  }

  useEffect(() => {
    poll()
    intervalRef.current = setInterval(poll, 2000)
    return () => clearInterval(intervalRef.current)
  }, [])

  // Auto-scroll to bottom when new lines arrive
  useEffect(() => {
    if (expanded) bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines, expanded])

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-0">
      {/* Expanded log panel */}
      {expanded && (
        <div className="mb-2 w-96 bg-gray-900 rounded-xl shadow-2xl border border-gray-700">
          {/* Progress bar */}
          {pct !== null && (
            <div className="px-3 pt-3 pb-1">
              {running ? (
                <>
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>{progress.current} / {progress.total}</span>
                    <span>{pct}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-teal-400 rounded-full transition-all duration-500"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </>
              ) : (
                <div className="flex items-center gap-2 text-sm text-teal-400 font-medium py-1">
                  <span>✓</span>
                  <span>資料抓取完成（共 {progress.total} 檔）</span>
                </div>
              )}
            </div>
          )}
          <div className="h-56 overflow-y-auto p-3 font-mono text-xs text-gray-200 space-y-0.5">
            {lines.length === 0 ? (
              <p className="text-gray-500">等待輸出...</p>
            ) : (
              lines.map((line, i) => (
                <div key={i} className={
                  line.startsWith('  ERROR') || line.startsWith('ERROR')
                    ? 'text-red-400'
                    : line.startsWith('===') || line.startsWith('>>>')
                      ? 'text-teal-300 font-semibold'
                      : line.includes('Finished') || line.includes('完成') || line.includes('Inserted')
                        ? 'text-green-400'
                        : 'text-gray-200'
                }>
                  {line || '\u00a0'}
                </div>
              ))
            )}
            <div ref={bottomRef} />
          </div>
        </div>
      )}

      {/* Status chip */}
      <div className="flex items-center gap-1 bg-gray-900 border border-gray-700 rounded-full shadow-lg">
        <button
          onClick={() => setExpanded(v => !v)}
          className="flex items-center gap-2 pl-3 pr-2 py-2 text-sm"
        >
          {running ? (
            <>
              <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse shrink-0" />
              <span className="text-white">抓取資料中...</span>
              {pct !== null && (
                <span className="text-xs text-gray-400 font-mono">{pct}%</span>
              )}
            </>
          ) : (
            <>
              <span className="inline-block w-2 h-2 rounded-full bg-teal-400 shrink-0" />
              <span className="text-gray-300">抓取完成</span>
            </>
          )}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`w-3.5 h-3.5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
            strokeLinecap="round" strokeLinejoin="round"
          >
            <path d="M18 15l-6-6-6 6" />
          </svg>
        </button>
        {!running && (
          <button
            onClick={onClose}
            className="pr-3 pl-1 py-2 text-gray-400 hover:text-white transition-colors text-base leading-none"
            aria-label="關閉"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  )
}
