export default function BlockLogicToggle({ logic, dispatch }) {
  return (
    <div className="flex justify-center py-1">
      <button
        onClick={() => dispatch({ type: 'SET_BLOCK_LOGIC', payload: logic === 'AND' ? 'OR' : 'AND' })}
        className={`px-5 py-1 rounded-full text-sm font-bold border-2 transition-all ${
          logic === 'AND'
            ? 'bg-blue-50 text-blue-700 border-blue-300 hover:bg-blue-100'
            : 'bg-orange-50 text-orange-700 border-orange-300 hover:bg-orange-100'
        }`}
        title="點擊切換區塊間邏輯"
      >
        {logic}
      </button>
    </div>
  )
}
