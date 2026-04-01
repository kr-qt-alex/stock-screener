import { useEffect, useRef, useState } from 'react'
import { getFetchLog } from '../api'

export default function FetchProgress({ onClose }) {
  const [lines, setLines] = useState([])
  const [running, setRunning] = useState(true)
  const bottomRef = useRef(null)
  const intervalRef = useRef(null)

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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-4 pointer-events-none">
      <div className="w-full max-w-3xl bg-gray-900 rounded-xl shadow-2xl border border-gray-700 pointer-events-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
          <div className="flex items-center gap-2">
            {running ? (
              <>
                <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-sm font-medium text-white">抓取資料中...</span>
              </>
            ) : (
              <>
                <span className="inline-block w-2 h-2 rounded-full bg-gray-400" />
                <span className="text-sm font-medium text-gray-300">抓取完成</span>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white text-lg leading-none px-1"
            aria-label="關閉"
          >
            ✕
          </button>
        </div>

        {/* Log output */}
        <div className="h-72 overflow-y-auto p-4 font-mono text-xs text-gray-200 space-y-0.5">
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
    </div>
  )
}
