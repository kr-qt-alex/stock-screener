export default function ConditionChips({ conditions }) {
  if (!conditions || !conditions.conditions?.length) return null

  const opLabels = { gte: '≥', lte: '≤', gt: '>', lt: '<', eq: '=' }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
      <p className="text-xs text-blue-600 font-medium mb-2">AI 解析結果</p>
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
                {rule.field} {opLabels[rule.operator] || rule.operator} {rule.value}
              </span>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
