SECTOR_MAP = {
    'Financial Services': '金融',
    'Technology': '電子',
    'Industrials': '傳產',
    'Healthcare': '生技醫療',
    'Communication Services': '傳媒',
    'Basic Materials': '原物料',
    'Energy': '能源',
    'Real Estate': '不動產',
    'Consumer Defensive': '民生消費',
    'Consumer Cyclical': '非必需消費',
    'Utilities': '公用事業',
}

INDUSTRY_MAP = {
    # 半導體
    'Semiconductors': '半導體',
    'Semiconductor Equipment': '半導體設備',
    # 電子零組件
    'Electronic Components': '電子零組件',
    'Electronics & Computer Distribution': '電子零組件',
    # 消費電子
    'Consumer Electronics': '消費電子',
    # 電腦硬體
    'Computer Hardware': '電腦硬體',
    'Computers': '電腦硬體',
    # 軟體
    'Software—Application': '應用軟體',
    'Software—Infrastructure': '系統軟體',
    'Software': '軟體',
    # 科技服務
    'Information Technology Services': '資訊服務',
    'Electronic Gaming & Multimedia': '電子娛樂',
    # 通訊設備
    'Communication Equipment': '通訊設備',
    'Telecom Services': '電信服務',
    # 被動元件 / PCB
    'Electronic Components & Parts': '電子零組件',
    # 金融
    'Banks—Regional': '銀行',
    'Banks—Diversified': '銀行',
    'Insurance—Life': '壽險',
    'Insurance—Property & Casualty': '產險',
    'Insurance—Diversified': '保險',
    'Capital Markets': '資本市場',
    'Asset Management': '資產管理',
    # 生技醫療
    'Biotechnology': '生技',
    'Pharmaceuticals': '製藥',
    'Medical Devices': '醫療器材',
    'Medical Instruments & Supplies': '醫療器材',
    'Drug Manufacturers': '製藥',
    # 不動產
    'Real Estate—Development': '建設開發',
    'Real Estate Services': '不動產服務',
    # 工業
    'Specialty Industrial Machinery': '工業機械',
    'Electrical Equipment & Parts': '電氣設備',
    'Industrial Distribution': '工業配銷',
    # 材料
    'Steel': '鋼鐵',
    'Chemicals': '化學',
    'Specialty Chemicals': '特用化學',
    'Paper & Paper Products': '紙業',
    'Aluminum': '鋁業',
    # 民生消費
    'Packaged Foods': '食品',
    'Beverages—Non-Alcoholic': '飲料',
    'Beverages—Brewers': '飲料',
    'Household & Personal Products': '家庭用品',
    'Grocery Stores': '零售',
    # 非必需消費
    'Auto Parts': '汽車零件',
    'Auto—Manufacturers': '汽車製造',
    'Textile Manufacturing': '紡織',
    'Apparel Manufacturing': '服飾',
    'Apparel Retail': '服飾零售',
    'Leisure': '休閒',
    'Restaurants': '餐飲',
    'Travel Services': '旅遊',
    # 其他
    'Conglomerates': '多角化企業',
    'Staffing & Employment Services': '人力資源',
    'Waste Management': '廢棄物管理',
    'Trucking': '陸運',
    'Marine Shipping': '海運',
    'Airlines': '航空',
    'Airports & Air Services': '航空服務',
}


def map_sector(sector_en: str) -> str:
    if not sector_en:
        return '其他'
    for key, value in SECTOR_MAP.items():
        if key.lower() in sector_en.lower() or sector_en.lower() in key.lower():
            return value
    return '其他'


def map_industry(industry_en: str) -> str:
    """Map yfinance industry string to Chinese. Falls back to English original if unmapped."""
    if not industry_en:
        return ''
    for key, value in INDUSTRY_MAP.items():
        if key.lower() == industry_en.lower():
            return value
    # Partial match fallback
    for key, value in INDUSTRY_MAP.items():
        if key.lower() in industry_en.lower():
            return value
    return industry_en  # keep English if no mapping found
