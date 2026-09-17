# Notion DB Manager

Notion Database 讀寫 CLI 工具，提供 Notion 資料庫與本機 JSON 檔案之間的雙向同步、部分更新與列操作。

---

## 1. 安裝與設定

### 安裝
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

pip install -e .
```

### 認證與專案設定
可透過命令列參數、環境變數或專案根目錄 `.env` 提供金鑰與定位設定：

```dotenv
NOTION_DB_MANAGER_TOKEN=secret_xxx
NOTION_DB_MANAGER_DATABASE_NAME=行程安排
# 若存在多個同名資料庫，可指定所屬專案/父頁面 (支援名稱、Page ID 或 Notion 網址)
NOTION_DB_MANAGER_PAGE=名古屋自由行
# 亦可直接以 Database ID/網址精準定位 (完全免搜尋)
# NOTION_DB_MANAGER_DATABASE_ID=c1387d89-9831-4c28-9ea9-952467d3df13

# [選填] Google Places API 金鑰 (用於 travel enrich-photos 指令)
GOOGLE_MAP_API=AIzaSy_xxx

# [選填] 並發數量 (預設: playwright=3, google=8)
NOTION_DB_MANAGER_CONCURRENCY=3
# [選填] 照片上傳至 Notion 並發數 (預設: 2, 上限: 3)
NOTION_DB_MANAGER_PUSH_CONCURRENCY=2
# [選填] 照片獲取是否預設僅補全空缺項目 (預設: false)
# NOTION_DB_MANAGER_MISSING_ONLY=true

```

- **優先順序**：命令列參數 > 環境變數 / `.env` > 終端互動輸入
- **檔案路徑慣例**：所有相對路徑統一預設存取專案根目錄下的 `output/` 資料夾（例如 `-o nagoya.json` 實際會寫入 `output/nagoya.json`）

---

## 2. 指令與參數列表 (Command Reference)

### 全域共用參數 (所有子指令皆可使用)
| 參數 | 說明 | 備註 |
| :--- | :--- | :--- |
| `--token` | Notion Integration Token | 若未提供，讀取 `.env` (`NOTION_DB_MANAGER_TOKEN`) 或終端提示輸入 |
| `--database-name` | 目標 Notion 資料庫名稱 | 若未提供，讀取 `.env` (`NOTION_DB_MANAGER_DATABASE_NAME`) 或終端提示輸入 |
| `--database-id` | 目標 Notion 資料庫 ID 或網址 | 可於 `.env` (`NOTION_DB_MANAGER_DATABASE_ID`) 定義，直接定位且免搜尋 |
| `--page` | 所屬專案頁/父頁面名稱、ID 或網址 | 可於 `.env` (`NOTION_DB_MANAGER_PAGE`) 定義，用以排除同名資料庫歧義 |
| `--google-api-key` | Google Cloud Places API 金鑰 | 若未提供，讀取 `.env` (`GOOGLE_MAP_API`) |

---

### Reader 指令群 (`notion-db-manager reader <action>`)
用於讀取 Notion 資料庫並匯出為標準 JSON。

| 指令 | 說明 | 必要與可選參數 |
| :--- | :--- | :--- |
| `export-all` | 匯出全部資料列與全部欄位 | `-o, --output <PATH>` [選填，預設 `yyyymmdd_hhmmss_export-all.json`]: 輸出 JSON 檔案路徑 |
| `export-columns` | 只匯出指定欄位 | `--columns <COL1> <COL2>...` [必要]: 欲匯出的欄位名稱<br>`-o, --output <PATH>` [選填，預設 `yyyymmdd_hhmmss_export-columns.json`]: 輸出 JSON 檔案路徑 |
| `export-rows` | 只匯出指定列索引 | `--rows <EXPR>` [必要]: 列索引表達式 (如 `1,3,5-7`)<br>`-o, --output <PATH>` [選填，預設 `yyyymmdd_hhmmss_export-rows.json`]: 輸出 JSON 檔案路徑 |

---

### Writer 指令群 (`notion-db-manager writer <action>`)
用於將 JSON 資料寫回 Notion 資料庫。

| 指令 | 說明 | 必要與可選參數 |
| :--- | :--- | :--- |
| `import-full` | 完整匯入 JSON 資料 | `--input <PATH>` [必要]: 輸入 JSON 檔案路徑<br>`--mode <append\|replace>` [必要]: 匯入模式 |
| `write-columns` | 自指定起點寫入部分欄位 | `--input <PATH>` [必要]: 輸入 JSON 檔案路徑<br>`--start-index <INT>` [選填，預設 `1`]: 起始列索引 (超出既有列數時自動新增) |
| `write-rows` | 整列資料寫入 | `--input <PATH>` [必要]: 輸入 JSON 檔案路徑<br>`--mode <append\|insert\|overwrite>` [必要]: 寫入模式<br>`--index <INT>` [`insert` 與 `overwrite` 必要]: 目標起始索引 |

#### 寫入模式 (Mode) 說明
- `append`：新增在資料庫末端。
- `replace`：清空資料庫中既有資料（封存原頁面），重新寫入全新資料。
- `insert`：在指定 index 插入新資料列，後續既有列的索引順位自動往後推移。
- `overwrite`：自指定 index 開始覆蓋既有列的可寫欄位，新資料未提供的可寫欄位將會清空。

---

### Travel 範本指令群 (`notion-db-manager travel <action>`)
專為 Travel Notion Template 定制的領域功能（支援地點、日文地點、屬性標籤、導航等欄位識別）。

| 指令 | 說明 | 必要與可選參數 |
| :--- | :--- | :--- |
| `enrich-photos` | 自動為旅遊地點獲取代表相片並儲存至本機 `output/images/<資料庫名稱>/`，產生 `manifest.json` | `--missing-only` [選填]: 僅抓取 Notion 中「照片」欄位仍為空的地點，已有照片者自動略過 (預設: 關閉，全數抓取)<br>`--provider <playwright\|google>` [選填，預設 `playwright`]: 爬蟲或官方 Places API<br>`--categories <CAT1> <CAT2>...` [選填]: 篩選特定類別 (若未指定則處理全部，包含交通)<br>`-c, --concurrency <INT>` [選填]: 並發抓取數量 (預設: playwright=3, google=8，亦可透過 `NOTION_DB_MANAGER_CONCURRENCY` 設定)<br>`--no-clean` [選填]: 執行前不清除輸出目錄中的舊圖 (預設會清空舊圖)<br>`--input <PATH>` [選填]: 讀取本機匯出的 JSON 檔 (離線模式，免呼叫 Notion API)<br>`--google-api-key <KEY>` [選填]: Google Cloud Places API 金鑰 |
| `push-photos` | 將本機已獲取的相片透過 Notion 官方 File Uploads API 原生上傳，並回填至資料庫「照片」欄位 | `-i, --input <PATH>` [選填]: 指定 `manifest.json` 檔案路徑 (預設為 `output/images/<資料庫名稱>/manifest.json`)<br>`-c, --concurrency <INT>` [選填]: 並發上傳數量 (預設: 2, 上限: 3，受 Notion 速率保護) |

---

## 3. 常用指令範例

### 匯出 (Reader)
```bash
# 匯出全部資料 (使用預設命名自動寫入 output/yyyymmdd_hhmmss_export-all.json)
notion-db-manager reader export-all

# 匯出全部資料到自訂路徑 (output/all.json)
notion-db-manager reader export-all -o all.json

# 當存在多個同名資料庫時，指定所屬專案頁面 (亦可直接寫在 .env 的 NOTION_DB_MANAGER_PAGE)
notion-db-manager reader export-all --database-name "行程安排" --page "名古屋自由行"

# 直接透過 Database ID 或網址定位匯出 (免搜尋)
notion-db-manager reader export-all --database-id "c1387d8998314c289ea9952467d3df13"

# 只匯出 Name, Status, Score 三個欄位 (不指定 -o 則自動產生 output/yyyymmdd_hhmmss_export-columns.json)
notion-db-manager reader export-columns --columns Name Status Score

# 只匯出第 1、第 3 以及第 5 至 7 列到自訂檔案
notion-db-manager reader export-rows --rows 1,3,5-7 -o rows.json
```

### 寫入 (Writer)
```bash
# 清空既有資料並全量匯入
notion-db-manager writer import-full --input all.json --mode replace

# 追加資料到現有資料庫後方
notion-db-manager writer import-full --input all.json --mode append

# 從第 3 列開始寫入指定欄位
notion-db-manager writer write-columns --input columns.json --start-index 3

# 在第 2 列插入新列 (後續資料自動順移)
notion-db-manager writer write-rows --input rows.json --mode insert --index 2

# 從第 5 列開始覆蓋資料
notion-db-manager writer write-rows --input rows.json --mode overwrite --index 5
```

### 旅遊照片獲取與回填 (Travel)
```bash
# 1. 全量抓取照片 (預設使用 Playwright 爬蟲，抓取所有項目包含交通，並寫入 output/images/<資料庫名稱>/)
notion-db-manager travel enrich-photos

# 2. 增量補全照片 (僅抓取 Notion「照片」欄位為空的地點，已有照片者自動略過)
notion-db-manager travel enrich-photos --missing-only

# 3. 篩選特定標籤 (如僅限景點與用餐) 並設定並發數為 4
notion-db-manager travel enrich-photos --categories 景點 用餐 --concurrency 4

# 4. 使用 Google Places API (讀取 .env 中的 GOOGLE_MAP_API，極速下載官方原圖)
notion-db-manager travel enrich-photos --provider google

# 5. 指定本機已匯出的 JSON 檔 (離線模式，免呼叫 Notion API)
notion-db-manager travel enrich-photos --input output/20260917_045325_export-all.json --provider google

# 6. 上傳本機照片回填 Notion (將 output/images/<資料庫名稱>/ 中的照片原生上傳至 Notion「照片」欄位)
notion-db-manager travel push-photos
```

---

## 4. 資料規格與注意事項

### JSON 交換規格範例
```json
{
  "meta": {
    "database_id": "...",
    "database_name": "Tasks",
    "export_type": "full",
    "selected_columns": [],
    "selected_rows": [],
    "order_property": "__NDM_INDEX__",
    "exported_at": "2026-09-17T00:00:00+00:00"
  },
  "rows": [
    {
      "index": 1,
      "page_id": "...",
      "properties": {
        "Name": { "type": "title", "value": "Task A" },
        "Status": { "type": "status", "value": "Done" },
        "Score": { "type": "number", "value": 100 }
      }
    }
  ]
}
```

### 注意事項
1. **排序列維護**：工具會自動在資料庫建立 `__NDM_INDEX__` (number) 欄位來固定列順序 (由 1 起算)。
2. **唯讀欄位處理**：公式 (formula)、彙總 (rollup)、建立時間等唯讀欄位會正常匯出，寫入時會自動忽略以確保成功寫入。