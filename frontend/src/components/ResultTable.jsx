import {
  useReactTable,
  getCoreRowModel,
  flexRender,
  createColumnHelper,
} from '@tanstack/react-table'

const columnHelper = createColumnHelper()

function formatMarketCap(val) {
  if (!val) return '-'
  return `${(val / 100000000).toLocaleString('zh-TW', { maximumFractionDigits: 0 })}億`
}

function formatVolume(val) {
  if (!val) return '-'
  if (val >= 1000000) return `${(val / 1000000).toFixed(1)}M`
  return val.toLocaleString()
}

const MARKET_BADGE = {
  listed:   { label: '上市', cls: 'bg-blue-100 text-blue-700' },
  otc:      { label: '上櫃', cls: 'bg-green-100 text-green-700' },
  emerging: { label: '興櫃', cls: 'bg-orange-100 text-orange-700' },
}

const columns = [
  columnHelper.accessor('symbol', {
    header: '代碼',
    cell: i => {
      const row = i.row.original
      const code = i.getValue()?.split('.')[0]
      const badge = MARKET_BADGE[row.market_type]
      return (
        <span className="flex items-center gap-1.5">
          <span className="font-mono text-sm font-medium">{code}</span>
          {badge && (
            <span className={`text-[10px] px-1 py-0.5 rounded font-medium ${badge.cls}`}>
              {badge.label}
            </span>
          )}
        </span>
      )
    },
  }),
  columnHelper.accessor('name', { header: '名稱' }),
  columnHelper.accessor('industry', {
    header: '產業',
    cell: i => {
      const value = i.getValue() || i.row.original.sector || '-'
      return <span className="text-xs px-2 py-0.5 bg-gray-100 rounded-full">{value}</span>
    },
  }),
  columnHelper.accessor('price', {
    header: '股價',
    cell: i => i.getValue()?.toFixed(2) ?? '-',
  }),
  columnHelper.accessor('pe_ratio', {
    header: '本益比',
    cell: i => i.getValue()?.toFixed(1) ?? '-',
  }),
  columnHelper.accessor('dividend_yield', {
    header: '殖利率 近12月',
    cell: i => {
      const v = i.getValue()
      if (v == null) return '-'
      return <span className={v >= 4 ? 'text-green-600 font-medium' : ''}>{v.toFixed(2)}%</span>
    },
  }),
  columnHelper.accessor('market_cap', {
    header: '市值',
    cell: i => formatMarketCap(i.getValue()),
  }),
  columnHelper.accessor('volume', {
    header: '成交量',
    cell: i => formatVolume(i.getValue()),
  }),
  columnHelper.accessor('monthly_revenue', {
    header: '最近月營收(千元)',
    cell: i => {
      const v = i.getValue()
      if (v == null) return <span className="text-gray-300">-</span>
      return <span>{v.toLocaleString()}</span>
    },
  }),
]

export default function ResultTable({ state, dispatch, onScreen }) {
  const table = useReactTable({
    data: state.results,
    columns,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
  })

  const totalPages = Math.ceil(state.total / state.pageSize)

  function handleSort(fieldKey) {
    let newOrder = 'desc'
    if (state.sortBy === fieldKey && state.sortOrder === 'desc') newOrder = 'asc'
    dispatch({ type: 'SET_SORT', payload: { sortBy: fieldKey, sortOrder: newOrder } })
    setTimeout(onScreen, 0)
  }

  const SORTABLE = {
    'price': 'price',
    'pe_ratio': 'pe_ratio',
    'dividend_yield': 'dividend_yield',
    'market_cap': 'market_cap',
    'volume': 'volume',
    'monthly_revenue': 'monthly_revenue',
  }

  if (state.loading) {
    return (
      <div className="flex justify-center items-center py-20 text-gray-400">
        <svg className="animate-spin h-8 w-8 mr-3 text-teal-500" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"/>
        </svg>
        資料載入中...
      </div>
    )
  }

  if (!state.results.length && state.total === 0 && !state.loading) {
    return (
      <div className="text-center py-12 text-gray-400 bg-white rounded-xl border border-gray-100">
        <p className="text-4xl mb-3">📊</p>
        <p className="font-medium">尚無資料</p>
        <p className="text-sm mt-1">請設定條件後點擊篩選，或確認資料庫已有資料</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-700">篩選結果 ({state.total} 檔)</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-600">
            {table.getHeaderGroups().map(hg => (
              <tr key={hg.id}>
                {hg.headers.map(header => {
                  const fieldKey = header.column.id
                  const isSortable = !!SORTABLE[fieldKey]
                  const isActive = state.sortBy === fieldKey
                  return (
                    <th
                      key={header.id}
                      onClick={isSortable ? () => handleSort(fieldKey) : undefined}
                      className={`px-4 py-3 text-left font-medium whitespace-nowrap ${
                        isSortable ? 'cursor-pointer hover:bg-gray-100 select-none' : ''
                      } ${isActive ? 'text-teal-700' : ''}`}
                    >
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {isActive && <span className="ml-1">{state.sortOrder === 'desc' ? '▲' : '▼'}</span>}
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, idx) => (
              <tr
                key={row.id}
                className={`border-t border-gray-50 hover:bg-teal-50 transition-colors ${
                  idx % 2 === 0 ? 'bg-white' : 'bg-gray-50/50'
                }`}
              >
                {row.getVisibleCells().map(cell => (
                  <td key={cell.id} className="px-4 py-2.5 text-gray-700">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="px-4 py-3 border-t flex items-center justify-center gap-2">
          <button
            onClick={() => { dispatch({ type: 'SET_PAGE', payload: state.page - 1 }); setTimeout(onScreen, 0) }}
            disabled={state.page <= 1}
            className="px-3 py-1 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            ‹
          </button>
          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            const p = state.page <= 4 ? i + 1 : state.page - 3 + i
            if (p < 1 || p > totalPages) return null
            return (
              <button
                key={p}
                onClick={() => { dispatch({ type: 'SET_PAGE', payload: p }); setTimeout(onScreen, 0) }}
                className={`w-8 h-8 rounded-lg text-sm transition-colors ${
                  p === state.page ? 'bg-teal-600 text-white' : 'hover:bg-gray-100 text-gray-600'
                }`}
              >
                {p}
              </button>
            )
          })}
          <button
            onClick={() => { dispatch({ type: 'SET_PAGE', payload: state.page + 1 }); setTimeout(onScreen, 0) }}
            disabled={state.page >= totalPages}
            className="px-3 py-1 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-50"
          >
            ›
          </button>
        </div>
      )}
    </div>
  )
}
