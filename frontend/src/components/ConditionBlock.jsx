import ConditionTag from './ConditionTag'

export default function ConditionBlock({ block, isSelected, canDelete, dispatch }) {
  return (
    <div
      onClick={() => dispatch({ type: 'SELECT_BLOCK', payload: block.id })}
      className={`bg-white rounded-xl p-4 border-2 cursor-pointer transition-all ${
        isSelected ? 'border-teal-500 shadow-md' : 'border-gray-200 hover:border-gray-300'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 font-medium">區塊內邏輯</span>
          <div className="flex bg-gray-100 rounded-md p-0.5">
            {['AND', 'OR'].map(t => (
              <button
                key={t}
                onClick={(e) => {
                  e.stopPropagation()
                  dispatch({ type: 'UPDATE_BLOCK_TYPE', payload: { id: block.id, blockType: t } })
                }}
                className={`px-2.5 py-0.5 rounded text-xs font-bold transition-colors ${
                  block.type === t ? 'bg-white text-teal-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          {isSelected && <span className="text-xs text-teal-600 font-medium">● 已選中</span>}
        </div>
        {canDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              dispatch({ type: 'REMOVE_BLOCK', payload: block.id })
            }}
            className="text-gray-400 hover:text-red-500 transition-colors text-lg leading-none"
            title="刪除區塊"
          >
            ×
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-2 min-h-[36px] items-start">
        {block.rules.map(rule => (
          <ConditionTag
            key={rule.id}
            rule={rule}
            blockId={block.id}
            dispatch={dispatch}
          />
        ))}
        {block.rules.length === 0 && (
          <span className="text-sm text-gray-400 italic">從條件庫新增條件，或點擊「新增條件」</span>
        )}
      </div>
    </div>
  )
}
