import { useState } from 'react'
import { CONDITION_LIBRARY } from '../constants/conditionLibrary'

export default function ConditionLibrary({ state, dispatch }) {
  const [search, setSearch] = useState('')
  const [collapsed, setCollapsed] = useState({})
  const [toast, setToast] = useState(false)

  function showToast() {
    setToast(true)
    setTimeout(() => setToast(false), 2000)
  }

  function addCondition(cond) {
    if (!state.selectedBlockId) {
      showToast()
      return
    }
    dispatch({
      type: 'ADD_RULE',
      payload: {
        blockId: state.selectedBlockId,
        rule: {
          field: cond.field,
          operator: cond.defaultOperator,
          value: cond.defaultValue,
          enabled: true,
        }
      }
    })
  }

  const filtered = CONDITION_LIBRARY.map(cat => ({
    ...cat,
    conditions: cat.conditions.filter(c => c.label.includes(search))
  })).filter(cat => cat.conditions.length > 0)

  return (
    <>
      <div
        className="fixed inset-0 bg-black/30 z-40"
        onClick={() => dispatch({ type: 'CLOSE_LIBRARY' })}
      />
      <aside className="fixed right-0 top-0 h-full w-80 bg-white shadow-2xl z-50 flex flex-col">
        <div className="p-4 border-b flex items-center justify-between">
          <h2 className="font-bold text-gray-800 text-lg">條件庫</h2>
          <button
            onClick={() => dispatch({ type: 'CLOSE_LIBRARY' })}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {toast && (
          <div className="mx-4 mt-2 p-2 bg-amber-100 text-amber-800 rounded-lg text-sm text-center">
            請先選擇一個區塊
          </div>
        )}

        <div className="p-4 border-b">
          <input
            placeholder="搜尋條件..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
          />
          {state.selectedBlockId ? (
            <p className="text-xs text-teal-600 mt-1.5">已選中區塊，點 + 新增條件</p>
          ) : (
            <p className="text-xs text-gray-400 mt-1.5">請先點擊左側一個區塊</p>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {filtered.map(cat => (
            <div key={cat.category}>
              <button
                onClick={() => setCollapsed(c => ({ ...c, [cat.category]: !c[cat.category] }))}
                className="w-full flex items-center justify-between py-1 text-sm font-semibold text-gray-700 hover:text-teal-700"
              >
                {cat.category}
                <span className="text-gray-400">{collapsed[cat.category] ? '▶' : '▼'}</span>
              </button>
              {!collapsed[cat.category] && (
                <div className="space-y-1 mt-1">
                  {cat.conditions.map(cond => (
                    <div key={cond.field} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-gray-50 group">
                      <span className="text-sm text-gray-700">{cond.label}</span>
                      <button
                        onClick={() => addCondition(cond)}
                        className="w-6 h-6 rounded-full bg-teal-100 text-teal-700 hover:bg-teal-200 font-bold text-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        +
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </aside>
    </>
  )
}
