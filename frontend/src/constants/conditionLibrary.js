export const CONDITION_LIBRARY = [
  {
    category: '基本面',
    conditions: [
      { field: 'pe_ratio', label: '本益比 (PE)', type: 'number', defaultOperator: 'lte', defaultValue: 20 },
      { field: 'forward_pe', label: '預估本益比', type: 'number', defaultOperator: 'lte', defaultValue: 20 },
      { field: 'dividend_yield', label: '殖利率 近12月 (%)', type: 'number', defaultOperator: 'gte', defaultValue: 3 },
      { field: 'market_cap', label: '市值 (億)', type: 'number', defaultOperator: 'gte', defaultValue: 10000000000, displayDivider: 100000000, displayUnit: '億' },
      { field: 'price', label: '股價', type: 'number', defaultOperator: 'lte', defaultValue: 100 },
      { field: 'monthly_revenue', label: '最近月營收 (千元)', type: 'number', defaultOperator: 'gte', defaultValue: 100000 },
    ]
  },
  {
    category: '族群分類',
    conditions: [
      { field: 'industry_or_sector', label: '產業', type: 'select', dynamicOptions: 'industry_options', options: [], defaultOperator: 'eq', defaultValue: '電子' },
      { field: 'market_type', label: '市場別', type: 'select', options: ['listed', 'otc', 'emerging'], optionLabels: { listed: '上市', otc: '上櫃', emerging: '興櫃' }, defaultOperator: 'eq', defaultValue: 'listed' },
    ]
  },
  {
    category: '技術面',
    conditions: [
      { field: 'week_52_high', label: '52週最高', type: 'number', defaultOperator: 'lte', defaultValue: 100 },
      { field: 'week_52_low', label: '52週最低', type: 'number', defaultOperator: 'gte', defaultValue: 50 },
      { field: 'volume', label: '成交量', type: 'number', defaultOperator: 'gte', defaultValue: 1000000 },
    ]
  },
]

export const OPERATORS = {
  number: [
    { value: 'gte', label: '≥' },
    { value: 'lte', label: '≤' },
    { value: 'gt', label: '>' },
    { value: 'lt', label: '<' },
    { value: 'eq', label: '=' },
  ],
  select: [
    { value: 'eq', label: '=' },
  ],
}

export function getFieldDef(fieldKey) {
  for (const cat of CONDITION_LIBRARY) {
    for (const cond of cat.conditions) {
      if (cond.field === fieldKey) return cond
    }
  }
  return null
}

export function formatRuleLabel(rule) {
  const def = getFieldDef(rule.field)
  if (!def) return `${rule.field} ${rule.operator} ${rule.value}`

  const opLabels = { gte: '≥', lte: '≤', gt: '>', lt: '<', eq: '=' }
  const opLabel = opLabels[rule.operator] || rule.operator

  let displayValue = rule.value
  if (def.displayDivider) {
    displayValue = `${(rule.value / def.displayDivider).toLocaleString()}${def.displayUnit || ''}`
  } else if (def.optionLabels) {
    displayValue = def.optionLabels[rule.value] || rule.value
  }

  return `${def.label} ${opLabel} ${displayValue}`
}
