import { useEffect, useMemo, useRef, useState } from 'react'
import { getFetchLog } from '../api'

const STEP_META = [
  { label: '快照資料', short: '快照' },
  { label: '月營收',   short: '月收' },
  { label: 'OHLCV',   short: 'OHLCV' },
]

export default function FetchProgress({ onClose, onComplete }) {
  const [lines, setLines] = useState([])
  const [running, setRunning] = useState(true)
  const [currentStep, setCurrentStep] = useState(0)   // 1-3 from backend, 0=idle
  const [stepsDone, setStepsDone] = useState([false, false, false])
  const [expanded, setExpanded] = useState(false)
  const bottomRef = useRef(null)
  const intervalRef = useRef(null)
  const unlockedRef = useRef(false)

  // Are we between two steps? (current step done but thread still running)
  const transitioning =
    running &&
    currentStep > 0 &&
    currentStep < 3 &&
    stepsDone[currentStep - 1] &&
    !stepsDone[currentStep]

  // Parse the last [N/M] from log lines for the current step's progress
  const progress = useMemo(() => {
    if (transitioning) return null
    for (let i = lines.length - 1; i >= 0; i--) {
      const m = lines[i].match(/\[(\d+)\/(\d+)\]/)
      if (m) return { current: parseInt(m[1]), total: parseInt(m[2]) }
    }
    return null
  }, [lines, transitioning])

  const pct = progress && progress.total > 0
    ? Math.round((progress.current / progress.total) * 100)
    : null

  const poll = async () => {
    try {
      const { data } = await getFetchLog()
      setLines(data.lines)
      setRunning(data.running)
      if (data.current_step !== undefined) setCurrentStep(data.current_step)
      if (data.steps_done)                 setStepsDone(data.steps_done)
      if (!data.running) {
        clearInterval(intervalRef.current)
        if (!unlockedRef.current) {
          unlockedRef.current = true
          onComplete?.()
        }
      }
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

  const activeIdx = currentStep > 0 ? currentStep - 1 : 0
  const chipLabel = transitioning
    ? `Step ${currentStep + 1}/3 — ${STEP_META[currentStep].label} 準備中`
    : `Step ${Math.max(currentStep, 1)}/3 — ${STEP_META[activeIdx].label}`

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-0">
      {/* Expanded log panel */}
      {expanded && (
        <div className="mb-2 w-96 bg-gray-900 rounded-xl shadow-2xl border border-gray-700">
          {/* Step tracker */}
          <div className="px-3 pt-3 pb-2 border-b border-gray-700">
            <div className="flex items-center gap-1">
              {STEP_META.map((meta, idx) => {
                const s = idx + 1
                const isDone    = stepsDone[idx]
                const isActive  = !isDone && currentStep === s
                return (
                  <div key={s} className="flex items-center gap-1 min-w-0">
                    <div className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${
                      isDone   ? 'bg-teal-900/50 text-teal-400' :
                      isActive ? 'bg-gray-700 text-white' :
                                 'bg-gray-800 text-gray-500'
                    }`}>
                      {isDone   ? '✓ ' :
                       isActive ? <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse mr-1" /> :
                                  null}
                      {s}/3 {meta.short}
                    </div>
                    {idx < 2 && <span className="text-gray-600 text-xs">→</span>}
                  </div>
                )
              })}
            </div>
            {/* Progress bar */}
            {running && (
              <div className="mt-2">
                {transitioning ? (
                  <div className="text-xs text-gray-400">
                    Step {currentStep}/3 完成，等待 Step {currentStep + 1}/3 開始...
                  </div>
                ) : pct !== null ? (
                  <>
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                      <span className="text-teal-400 font-medium">{chipLabel}</span>
                      <span>{progress.current} / {progress.total}</span>
                    </div>
                    <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-teal-400 rounded-full transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </>
                ) : null}
              </div>
            )}
            {!running && (
              <div className="flex items-center gap-2 text-sm text-teal-400 font-medium mt-1">
                <span>✓</span>
                <span>全部完成</span>
              </div>
            )}
          </div>

          {/* Log output */}
          <div className="h-48 overflow-y-auto p-3 font-mono text-xs text-gray-200 space-y-0.5">
            {lines.length === 0 ? (
              <p className="text-gray-500">等待輸出...</p>
            ) : (
              lines.map((line, i) => (
                <div key={i} className={
                  line.startsWith('  ERROR') || line.startsWith('ERROR')
                    ? 'text-red-400'
                    : line.startsWith('━━') || line.startsWith('>>>')
                      ? 'text-teal-300 font-semibold'
                      : line.includes('Finished') || line.includes('完成') || line.includes('Inserted') || line.includes('跳過')
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
              <span className={`inline-block w-2 h-2 rounded-full shrink-0 ${
                transitioning ? 'bg-yellow-400 animate-pulse' : 'bg-green-400 animate-pulse'
              }`} />
              <span className="text-white">{chipLabel}</span>
              {pct !== null && !transitioning && (
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
