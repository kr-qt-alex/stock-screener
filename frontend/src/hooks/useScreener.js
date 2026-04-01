import { useCallback } from 'react'
import { screenStocks } from '../api'

export function useScreener(state, dispatch) {
  const runScreen = useCallback(async () => {
    dispatch({ type: 'SET_LOADING', payload: true })
    dispatch({ type: 'SET_ERROR', payload: null })

    try {
      let payload = {
        sort_by: state.sortBy,
        sort_order: state.sortOrder,
        page: state.page,
        page_size: state.pageSize,
      }

      if (state.mode === 'natural_language') {
        payload.mode = 'natural_language'
        payload.query = state.nlQuery
      } else {
        payload.mode = 'manual'
        payload.filters = {
          conditions: state.blocks.map(block => ({
            block_type: block.type,
            rules: block.rules
              .filter(r => r.enabled)
              .map(r => ({ field: r.field, operator: r.operator, value: r.value }))
          })).filter(b => b.rules.length > 0),
          block_logic: state.blockLogic,
        }
      }

      const res = await screenStocks(payload)
      const data = res.data

      dispatch({ type: 'SET_RESULTS', payload: { results: data.results, total: data.total } })
      if (data.parsed_conditions) {
        dispatch({ type: 'SET_PARSED', payload: data.parsed_conditions })
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || '篩選失敗，請稍後再試'
      dispatch({ type: 'SET_ERROR', payload: msg })
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false })
    }
  }, [state, dispatch])

  return { runScreen }
}
