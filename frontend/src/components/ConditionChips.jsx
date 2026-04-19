import { formatRuleLabel } from '../constants/conditionLibrary'

export default function ConditionChips({ conditions, reason }) {
  if (!conditions || !conditions.conditions?.length) return null

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
      <p className="text-xs text-blue-600 font-medium mb-2">AI 解析結果</p>
      {reason && (
        <p className="text-xs text-gray-600 mb-3 leading-relaxed">{reason}</p>
      )}
      <div className="flex flex-wrap gap-2">
        {conditions.conditions.map((block, bi) => (
          <div key={bi} className="flex flex-wrap gap-1.5 items-center">
            {bi > 0 && (
              <span className="text-xs font-bold text-orange-600 bg-orange-100 px-2 py-0.5 rounded-full">
                {conditions.block_logic}
              </span>
            )}
            <span className="text-xs text-gray-500 bg-white border rounded-full px-2 py-0.5">
              {block.block_type}
            </span>
            {block.rules.map((rule, ri) => (
              <span key={ri} className="text-xs bg-blue-100 text-blue-800 px-3 py-1 rounded-full font-medium">
                {formatRuleLabel(rule)}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
