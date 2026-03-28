# 票券監控 Discord Bot

監控活動票券狀態，當票券開放時自動發送 Discord 通知

## 功能

- 每 60 秒自動檢查票券狀態
- 偵測到 `IN_STOCK` 或 `NEARLY_SOLD_OUT` 時，在指定頻道發送通知
- 支援透過 Discord Slash Command 管理監控清單

### Slash Commands

| 指令 | 說明 |
|------|------|
| `/add_ticket <name> <url>` | 新增一個監控票券（自動綁定當前頻道） |
| `/remove_ticket` | 透過下拉選單刪除監控票券 |
| `/status` | 列出目前所有監控中的票券 |

## 安裝

**需求：** Python 3.10+

```bash
pip install discord.py python-dotenv aiohttp curl_cffi
```

## 設定

**1. 設定 Discord Token**

複製 `.env.example` 為 `.env`，填入 Bot Token：

```
DISCORD_TOKEN=your_token_here
```

**2. 設定初始監控清單（可選）**

2-1 複製 `config_example.json` 為 `config.json`：

```json
{
    "targets": [
        {
            "name": "活動名稱",
            "url": "https://kktix.com/events/xxx/registrations/new",
            "type": "kktix",
            "channel_id": 1234567890
        }
    ]
}
```

> `channel_id` 為要發送通知的 Discord 文字頻道 ID。

2-2 直接用 `/add_ticket` 指令新增，會自動使用當前頻道。

## 執行

```bash
python main.py
```

## 專案結構

```
.
├── main.py                  # Bot 入口
├── config.json              # 監控目標設定（執行時自動維護）
├── config_example.json      # 範例
├── .env                     # Discord Token
├── cogs/
│   └── monitor_cmd.py       # 監控邏輯與 Slash Commands
└── scrapers/
    ├── base.py              # Scraper 抽象基底類別
    ├── kktix_scraper.py     # KKTIX API 爬蟲
    └── simple_scraper.py    # 通用關鍵字爬蟲（備用）
```
