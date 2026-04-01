import { useState, useRef } from 'react'
import ConditionPopover from './ConditionPopover'
import { formatRuleLabel } from '../constants/conditionLibrary'

export default function ConditionTag({ rule, blockId, dispatch }) {
  const [popoverOpen, setPopoverOpen] = useState(false)
  const tagRef = useRef(null)

  return (
    <div className="relative" ref={tagRef}>
      <div
        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium cursor-pointer border transition-all ${
          rule.enabled
            ? 'bg-teal-50 text-teal-800 border-teal-200 hover:bg-teal-100'
            : 'bg-gray-100 text-gray-400 border-gray-200 line-through'
        }`}
        onClick={(e) => {
          e.stopPropagation()
          setPopoverOpen(o => !o)
        }}
      >
        <span
          onClick={(e) => {
            e.stopPropagation()
            dispatch({ type: 'TOGGLE_RULE', payload: { blockId, ruleId: rule.id } })
          }}
          className="w-2 h-2 rounded-full inline-block"
          style={{ background: rule.enabled ? '#0d9488' : '#9ca3af' }}
          title={rule.enabled ? '停用' : '啟用'}
        />
        {formatRuleLabel(rule)}
        <button
          onClick={(e) => {
            e.stopPropagation()
            dispatch({ type: 'REMOVE_RULE', payload: { blockId, ruleId: rule.id } })
          }}
          className="text-current opacity-50 hover:opacity-100 ml-0.5 text-base leading-none"
        >
          ×
        </button>
      </div>

      {popoverOpen && (
        <ConditionPopover
          rule={rule}
          blockId={blockId}
          dispatch={dispatch}
          onClose={() => setPopoverOpen(false)}
          anchorRef={tagRef}
        />
      )}
    </div>
  )
}
