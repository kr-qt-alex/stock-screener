import { useEffect, useState } from 'react'
import { triggerFetch, triggerFullFetch, getDataRange } from '../api'
import FetchProgress from './FetchProgress'

function formatDate(iso) {
  if (!iso) return '—'
  const [y, m, d] = iso.split('-')
  return `${y}/${m}/${d}`
}

export default function Header({ mode, dispatch }) {
  const [showLog, setShowLog] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [dateRange, setDateRange] = useState({ from: null, to: null })

  const loadRange = async () => {
    try {
      const { data } = await getDataRange()
      setDateRange(data)
    } catch {
      // backend not ready yet
    }
  }

  useEffect(() => { loadRange() }, [])

  const handleFetch = async () => {
    try {
      setFetching(true)
      await triggerFetch()
      setShowLog(true)
    } catch {
      setFetching(false)
    }
  }

  const handleFullFetch = async () => {
    try {
      setFetching(true)
      await triggerFullFetch()
      setShowLog(true)
    } catch {
      setFetching(false)
    }
  }

  const handleLogClose = () => {
    setShowLog(false)
    setFetching(false)
    loadRange()  // refresh date range after fetch completes
  }

  const hasRange = dateRange.from && dateRange.to

  return (
    <>
      <header className="bg-teal-700 text-white shadow-lg">
        {/* Main row */}
        <div className="max-w-7xl mx-auto px-4 pt-4 pb-2 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">台股 AI 篩選器</h1>
            <p className="text-teal-200 text-sm">每日盤後資料分析</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleFetch}
              disabled={fetching}
              className="px-3 py-1.5 text-sm rounded-md border border-teal-400 text-teal-100 hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {fetching ? '抓取中...' : '更新資料'}
            </button>
            <div className="flex bg-teal-800 rounded-lg p-1 gap-1">
              <button
                onClick={() => dispatch({ type: 'SET_MODE', payload: 'manual' })}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  mode === 'manual' ? 'bg-white text-teal-700' : 'text-teal-200 hover:text-white'
                }`}
              >
                積木模式
              </button>
              <button
                onClick={() => dispatch({ type: 'SET_MODE', payload: 'natural_language' })}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  mode === 'natural_language' ? 'bg-white text-teal-700' : 'text-teal-200 hover:text-white'
                }`}
              >
                AI 模式
              </button>
            </div>
          </div>
        </div>

        {/* Date range row */}
        <div className="max-w-7xl mx-auto px-4 pb-3 flex items-center gap-2">
          <span className="text-teal-300 text-xs">歷史資料區間</span>
          <span className="text-white text-xs font-mono">
            {hasRange
              ? `${formatDate(dateRange.from)}　～　${formatDate(dateRange.to)}`
              : '尚無資料'}
          </span>
          <button
            onClick={handleFullFetch}
            disabled={fetching}
            title="完整回補（重新掃描整個保留窗口補齊缺漏，適合修改保留年數後使用）"
            className="ml-1 p-1 rounded text-teal-300 hover:text-white hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {/* Refresh / sync icon */}
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
              <path d="M21 3v5h-5"/>
              <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
              <path d="M3 21v-5h5"/>
            </svg>
          </button>
        </div>
      </header>

      {showLog && <FetchProgress onClose={handleLogClose} />}
    </>
  )
}
