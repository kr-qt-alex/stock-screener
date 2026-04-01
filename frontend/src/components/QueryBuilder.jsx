import ConditionBlock from './ConditionBlock'
import BlockLogicToggle from './BlockLogicToggle'

export default function QueryBuilder({ state, dispatch, onScreen }) {
  return (
    <div className="space-y-2">
      {state.blocks.map((block, idx) => (
        <div key={block.id}>
          <ConditionBlock
            block={block}
            isSelected={state.selectedBlockId === block.id}
            canDelete={state.blocks.length > 1}
            dispatch={dispatch}
          />
          {idx < state.blocks.length - 1 && (
            <BlockLogicToggle logic={state.blockLogic} dispatch={dispatch} />
          )}
        </div>
      ))}

      <div className="flex gap-2 pt-2">
        <button
          onClick={() => dispatch({ type: 'ADD_BLOCK' })}
          className="px-4 py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-500 hover:border-teal-400 hover:text-teal-600 transition-colors text-sm"
        >
          + 新增區塊
        </button>
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={onScreen}
          disabled={state.loading}
          className="px-6 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
        >
          {state.loading ? (
            <>
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"/>
              </svg>
              篩選中...
            </>
          ) : '🔍 篩選'}
        </button>
        <button
          onClick={() => dispatch({ type: 'TOGGLE_LIBRARY' })}
          className="px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors text-sm"
        >
          條件庫
        </button>
      </div>
    </div>
  )
}
