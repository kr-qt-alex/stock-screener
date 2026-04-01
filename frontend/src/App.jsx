import { useReducer } from 'react'
import Header from './components/Header'
import QueryBuilder from './components/QueryBuilder'
import ConditionLibrary from './components/ConditionLibrary'
import NLSearchBar from './components/NLSearchBar'
import ConditionChips from './components/ConditionChips'
import ResultTable from './components/ResultTable'
import { useScreener } from './hooks/useScreener'

const initialState = {
  mode: 'manual',
  blocks: [
    {
      id: 'block-1',
      type: 'AND',
      rules: [
        { id: 'rule-1', field: 'pe_ratio', operator: 'lte', value: 20, enabled: true },
        { id: 'rule-2', field: 'dividend_yield', operator: 'gte', value: 3, enabled: true },
      ]
    }
  ],
  blockLogic: 'AND',
  selectedBlockId: 'block-1',
  libraryOpen: false,
  nlQuery: '',
  parsedConditions: null,
  results: [],
  total: 0,
  page: 1,
  pageSize: 20,
  sortBy: 'dividend_yield',
  sortOrder: 'desc',
  loading: false,
  error: null,
  summary: null,
}

let nextId = 10

function reducer(state, action) {
  switch (action.type) {
    case 'SET_MODE':
      return { ...state, mode: action.payload, results: [], total: 0, error: null, parsedConditions: null }
    case 'ADD_BLOCK':
      return { ...state, blocks: [...state.blocks, { id: `block-${++nextId}`, type: 'AND', rules: [] }] }
    case 'REMOVE_BLOCK':
      if (state.blocks.length <= 1) return state
      return {
        ...state,
        blocks: state.blocks.filter(b => b.id !== action.payload),
        selectedBlockId: state.selectedBlockId === action.payload ? null : state.selectedBlockId
      }
    case 'UPDATE_BLOCK_TYPE':
      return { ...state, blocks: state.blocks.map(b => b.id === action.payload.id ? { ...b, type: action.payload.blockType } : b) }
    case 'ADD_RULE': {
      const { blockId, rule } = action.payload
      return { ...state, blocks: state.blocks.map(b => b.id === blockId ? { ...b, rules: [...b.rules, { ...rule, id: `rule-${++nextId}` }] } : b) }
    }
    case 'REMOVE_RULE': {
      const { blockId, ruleId } = action.payload
      return { ...state, blocks: state.blocks.map(b => b.id === blockId ? { ...b, rules: b.rules.filter(r => r.id !== ruleId) } : b) }
    }
    case 'UPDATE_RULE': {
      const { blockId, ruleId, changes } = action.payload
      return { ...state, blocks: state.blocks.map(b => b.id === blockId ? { ...b, rules: b.rules.map(r => r.id === ruleId ? { ...r, ...changes } : r) } : b) }
    }
    case 'TOGGLE_RULE': {
      const { blockId, ruleId } = action.payload
      return { ...state, blocks: state.blocks.map(b => b.id === blockId ? { ...b, rules: b.rules.map(r => r.id === ruleId ? { ...r, enabled: !r.enabled } : r) } : b) }
    }
    case 'SET_BLOCK_LOGIC':
      return { ...state, blockLogic: action.payload }
    case 'SELECT_BLOCK':
      return { ...state, selectedBlockId: action.payload }
    case 'TOGGLE_LIBRARY':
      return { ...state, libraryOpen: !state.libraryOpen }
    case 'CLOSE_LIBRARY':
      return { ...state, libraryOpen: false }
    case 'SET_NL_QUERY':
      return { ...state, nlQuery: action.payload }
    case 'SET_PARSED':
      return { ...state, parsedConditions: action.payload }
    case 'SET_RESULTS':
      return { ...state, results: action.payload.results, total: action.payload.total }
    case 'SET_LOADING':
      return { ...state, loading: action.payload }
    case 'SET_ERROR':
      return { ...state, error: action.payload }
    case 'SET_PAGE':
      return { ...state, page: action.payload }
    case 'SET_SORT':
      return { ...state, sortBy: action.payload.sortBy, sortOrder: action.payload.sortOrder, page: 1 }
    default:
      return state
  }
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState)
  const { runScreen } = useScreener(state, dispatch)

  return (
    <div className="min-h-screen bg-gray-50">
      <Header mode={state.mode} dispatch={dispatch} />

      <main className="max-w-7xl mx-auto px-4 py-6">
        {state.mode === 'manual' ? (
          <QueryBuilder state={state} dispatch={dispatch} onScreen={runScreen} />
        ) : (
          <div className="space-y-4">
            <NLSearchBar state={state} dispatch={dispatch} onScreen={runScreen} />
            {state.parsedConditions && (
              <ConditionChips conditions={state.parsedConditions} />
            )}
          </div>
        )}

        {state.error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {state.error}
          </div>
        )}

        <div className="mt-6">
          <ResultTable state={state} dispatch={dispatch} onScreen={runScreen} />
        </div>
      </main>

      {state.libraryOpen && (
        <ConditionLibrary state={state} dispatch={dispatch} />
      )}
    </div>
  )
}
