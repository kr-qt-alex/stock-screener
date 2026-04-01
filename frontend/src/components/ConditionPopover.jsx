import { useEffect, useRef, useState } from 'react'
import { getFieldDef, OPERATORS } from '../constants/conditionLibrary'
import { getSectors } from '../api'

export default function ConditionPopover({ rule, blockId, dispatch, onClose }) {
  const popRef = useRef(null)
  const def = getFieldDef(rule.field)
  const [dynamicOpts, setDynamicOpts] = useState([])

  useEffect(() => {
    if (def?.dynamicOptions) {
      getSectors().then(({ data }) => setDynamicOpts(data.sectors)).catch(() => {})
    }
  }, [def?.dynamicOptions])

  useEffect(() => {
    function handleClick(e) {
      if (popRef.current && !popRef.current.contains(e.target)) {
        onClose()
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  const operators = def ? OPERATORS[def.type] || OPERATORS.number : OPERATORS.number

  function update(changes) {
    dispatch({ type: 'UPDATE_RULE', payload: { blockId, ruleId: rule.id, changes } })
  }

  return (
    <div
      ref={popRef}
      className="absolute z-50 top-full mt-1 left-0 bg-white border border-gray-200 rounded-xl shadow-xl p-4 w-64"
      onClick={e => e.stopPropagation()}
    >
      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">欄位</label>
          <div className="text-sm font-medium text-gray-800 bg-gray-50 rounded-lg px-3 py-2">
            {def?.label || rule.field}
          </div>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">運算子</label>
          <select
            value={rule.operator}
            onChange={e => update({ operator: e.target.value })}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
          >
            {operators.map(op => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1">值</label>
          {def?.type === 'select' ? (
            <select
              value={rule.value}
              onChange={e => update({ value: e.target.value })}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
            >
              {(def.dynamicOptions ? dynamicOpts : def.options).map(opt => (
                <option key={opt} value={opt}>
                  {def.optionLabels?.[opt] || opt}
                </option>
              ))}
            </select>
          ) : (
            <input
              type="number"
              value={def?.displayDivider ? rule.value / def.displayDivider : rule.value}
              onChange={e => {
                const raw = parseFloat(e.target.value)
                update({ value: def?.displayDivider ? raw * def.displayDivider : raw })
              }}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
            />
          )}
          {def?.displayUnit && <span className="text-xs text-gray-400 mt-1 block">單位：{def.displayUnit}</span>}
        </div>
      </div>

      <button
        onClick={onClose}
        className="mt-3 w-full py-1.5 bg-teal-600 text-white text-sm rounded-lg hover:bg-teal-700 transition-colors"
      >
        確定
      </button>
    </div>
  )
}
