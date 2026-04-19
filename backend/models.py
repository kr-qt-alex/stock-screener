from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any


class Rule(BaseModel):
    field: str
    operator: str  # eq, gt, gte, lt, lte
    value: Any


class Block(BaseModel):
    block_type: Literal['AND', 'OR']
    rules: List[Rule]


class Filters(BaseModel):
    conditions: List[Block]
    block_logic: Literal['AND', 'OR'] = 'AND'


class ScreenRequest(BaseModel):
    mode: Literal['manual', 'natural_language'] = 'manual'
    filters: Optional[Filters] = None
    query: Optional[str] = None
    sort_by: str = 'dividend_yield'
    sort_order: Literal['asc', 'desc'] = 'desc'
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class StockResult(BaseModel):
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    sector_en: Optional[str] = None
    industry: Optional[str] = None
    industry_en: Optional[str] = None
    market_type: Optional[str] = None
    price: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    dividend_yield: Optional[float] = None
    market_cap: Optional[int] = None
    volume: Optional[int] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None
    monthly_revenue: Optional[int] = None


class ScreenResponse(BaseModel):
    mode: str
    parsed_conditions: Optional[Filters] = None
    ai_reason: Optional[str] = None
    results: List[StockResult]
    total: int
    page: int
    page_size: int
