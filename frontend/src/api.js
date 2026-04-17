import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

export const screenStocks = (payload) => api.post('/api/screen', payload)
export const getSectors = () => api.get('/api/sectors')
export const getIndustries = () => api.get('/api/industries')
export const getIndustryOptions = () => api.get('/api/industry_options')
export const getHealth = () => api.get('/api/health')
export const getSummary = (results, query) => api.post('/api/summarize', { results, query })
export const triggerFetch = () => api.post('/api/fetch')
export const triggerFullFetch = () => api.post('/api/fetch/full')
export const getFetchLog = () => api.get('/api/fetch/log')
export const getDataRange = () => api.get('/api/data/range')

export default api
