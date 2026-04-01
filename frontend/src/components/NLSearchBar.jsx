export default function NLSearchBar({ state, dispatch, onScreen }) {
  function handleKeyDown(e) {
    if (e.key === 'Enter') onScreen()
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-600 mb-3">用自然語言描述篩選條件</h2>
      <div className="flex gap-3">
        <input
          type="text"
          value={state.nlQuery}
          onChange={e => dispatch({ type: 'SET_NL_QUERY', payload: e.target.value })}
          onKeyDown={handleKeyDown}
          placeholder="例如：本益比低於 15 的金融股、殖利率大於 5% 的高股息股..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-teal-400 text-sm"
        />
        <button
          onClick={onScreen}
          disabled={state.loading || !state.nlQuery.trim()}
          className="px-5 py-2.5 bg-teal-600 text-white rounded-lg font-medium hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
        >
          {state.loading ? (
            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z"/>
            </svg>
          ) : '🔍'} 篩選
        </button>
      </div>
    </div>
  )
}
