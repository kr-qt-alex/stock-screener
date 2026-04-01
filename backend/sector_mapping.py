SECTOR_MAP = {
    'Financial Services': '金融',
    'Technology': '電子',
    'Semiconductors': '半導體',
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


def map_sector(sector_en: str) -> str:
    if not sector_en:
        return '其他'
    for key, value in SECTOR_MAP.items():
        if key.lower() in sector_en.lower() or sector_en.lower() in key.lower():
            return value
    return '其他'
