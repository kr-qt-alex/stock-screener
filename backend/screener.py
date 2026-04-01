from typing import Tuple, List, Any
from models import Filters

ALLOWED_FIELDS = {
    'sector', 'sector_en', 'market_type', 'price', 'pe_ratio',
    'forward_pe', 'dividend_yield', 'market_cap', 'volume',
    'week_52_high', 'week_52_low', 'revenue_growth'
}

OPERATOR_MAP = {
    'eq': '=',
    'gt': '>',
    'gte': '>=',
    'lt': '<',
    'lte': '<='
}

ALLOWED_SORT_FIELDS = ALLOWED_FIELDS | {'symbol', 'name'}


def build_where_clause(filters: Filters) -> Tuple[str, List[Any]]:
    """Build the SQL WHERE clause from a Filters object.

    Returns a tuple of (where_sql, params).
    If there are no conditions, returns ('1=1', []).
    """
    params: List[Any] = []
    block_clauses: List[str] = []

    for block in filters.conditions:
        rule_clauses: List[str] = []
        for rule in block.rules:
            if rule.field not in ALLOWED_FIELDS:
                raise ValueError(f"Invalid field: {rule.field}")
            op = OPERATOR_MAP.get(rule.operator)
            if op is None:
                raise ValueError(f"Invalid operator: {rule.operator}")
            rule_clauses.append(f"{rule.field} {op} ?")
            params.append(rule.value)

        if not rule_clauses:
            continue

        inner_logic = block.block_type  # 'AND' or 'OR'
        joined = f' {inner_logic} '.join(rule_clauses)
        block_sql = f'({joined})'
        block_clauses.append(block_sql)

    if not block_clauses:
        return "1=1", []

    outer_logic = filters.block_logic
    where_sql = f' {outer_logic} '.join(block_clauses)
    return where_sql, params


def build_query(
    filters: Filters,
    sort_by: str = 'dividend_yield',
    sort_order: str = 'desc',
    page: int = 1,
    page_size: int = 20
) -> Tuple[str, str, List[Any], List[Any]]:
    """Build SELECT and COUNT SQL queries from screening parameters.

    Returns a tuple of:
        (select_sql, count_sql, select_params, count_params)

    select_params includes page_size and offset appended at the end.
    count_params does NOT include page_size/offset.
    """
    if sort_by not in ALLOWED_SORT_FIELDS:
        sort_by = 'dividend_yield'
    if sort_order not in ('asc', 'desc'):
        sort_order = 'desc'

    where_clause, params = build_where_clause(filters)
    offset = (page - 1) * page_size

    # Use a CASE expression to push NULLs to the end of the result set
    # regardless of ASC/DESC order.
    select_sql = f"""
        SELECT symbol, name, sector, sector_en, market_type, price, pe_ratio, forward_pe,
               dividend_yield, market_cap, volume, week_52_high, week_52_low, revenue_growth
        FROM stocks
        WHERE {where_clause}
        ORDER BY CASE WHEN {sort_by} IS NULL THEN 1 ELSE 0 END, {sort_by} {sort_order}
        LIMIT ? OFFSET ?
    """

    count_sql = f"SELECT COUNT(*) FROM stocks WHERE {where_clause}"

    select_params: List[Any] = params + [page_size, offset]
    count_params: List[Any] = params

    return select_sql, count_sql, select_params, count_params
