import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
from models import Filters

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

AI_ENABLED = os.getenv('AI_ENABLED', 'true').lower() == 'true'

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_FIELDS_DESC = """\
可用欄位與運算子：
  - sector (產業): 金融/半導體/傳產/電子/生技醫療/傳媒/原物料/能源/不動產/民生消費/非必需消費/公用事業
  - pe_ratio (本益比): 數值，運算子 gt/gte/lt/lte/eq
  - forward_pe (預估本益比): 數值
  - dividend_yield (殖利率 %): 數值
  - market_cap (市值 TWD): 數值
  - price (股價): 數值
  - volume (成交量): 數值
  - market_type (市場): listed(上市) / otc(上櫃)
"""

_OUTPUT_FORMAT = """\
只輸出以下 JSON 格式，不要任何說明文字：
{
  "conditions": [
    {
      "block_type": "AND",
      "rules": [
        { "field": "欄位名", "operator": "運算子", "value": 值 }
      ]
    }
  ],
  "block_logic": "AND"
}
若無法解析，輸出：{ "error": "無法解析，請更明確描述條件" }
"""


# ---------------------------------------------------------------------------
# Claude CLI call (sync, runs in thread pool to avoid blocking event loop)
# ---------------------------------------------------------------------------

def _get_claude_cmd() -> str:
    """Resolve the claude CLI executable path (handles Windows .cmd extension)."""
    candidates = ['claude', 'claude.cmd'] if sys.platform == 'win32' else ['claude']
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    # Last resort: check the known npm global bin path on Windows
    if sys.platform == 'win32':
        fallback = os.path.expandvars(r'%APPDATA%\npm\claude.cmd')
        if os.path.exists(fallback):
            return fallback
    raise FileNotFoundError(
        "找不到 claude CLI，請確認 Claude Code 已安裝並登入"
    )


def _call_claude_cli(query: str) -> str:
    """Call the local Claude Code CLI and return the raw text response."""
    import tempfile, pathlib

    claude_cmd = _get_claude_cmd()
    full_prompt = (
        f"請將以下台股篩選需求轉換為 JSON 篩選條件。\n\n"
        f"篩選需求：「{query}」\n\n"
        f"{_FIELDS_DESC}\n"
        f"注意事項：\n"
        f"- 模糊詞彙請合理推測（短線/動能 → 高成交量；便宜 → 低本益比）\n"
        f"- 無法從現有欄位表達的條件請忽略\n"
        f"- 包含「或」邏輯時使用 block_type: OR\n\n"
        f"{_OUTPUT_FORMAT}"
    )

    # Write prompt to a temp file to avoid any shell quoting / encoding issues
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                     suffix='.txt', delete=False) as f:
        f.write(full_prompt)
        prompt_file = f.name

    try:
        # Pass prompt via stdin to avoid Windows command-line encoding issues
        result = subprocess.run(
            [claude_cmd, '-p', '-'],
            input=full_prompt.encode('utf-8'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        stdout = result.stdout.decode('utf-8', errors='replace').strip()
        stderr = result.stderr.decode('utf-8', errors='replace').strip()

        if result.returncode != 0:
            raise RuntimeError(f"Claude CLI 執行失敗：{stderr}")
        return stdout
    finally:
        pathlib.Path(prompt_file).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict:
    """
    Robustly extract and parse a JSON object from Claude's raw output.
    Handles: plain JSON, markdown code fences, leading/trailing prose.
    """
    text = text.strip()

    # 1. Strip markdown code fences  ```json ... ``` or ``` ... ```
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence:
        text = fence.group(1).strip()

    # 2. If still not starting with '{', find the first '{' and last '}'
    if not text.startswith('{'):
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end + 1]

    return json.loads(text)


# ---------------------------------------------------------------------------
# Public async interface
# ---------------------------------------------------------------------------

async def parse_natural_language(query: str) -> Filters:
    """Parse a natural-language screening query into a Filters object via Claude CLI."""
    if not AI_ENABLED:
        raise ValueError("AI 功能已關閉（AI_ENABLED=false），請使用手動篩選模式")

    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _call_claude_cli, query)

    # Extract JSON object from output (handles extra text / markdown fences)
    data = _extract_json(raw)

    if "error" in data:
        raise ValueError(data["error"])

    return Filters(**data)
