# Notion DB Manager

這是一個 Python CLI 工具，提供 Notion database 的 Reader / Writer 功能。

工具會用資料庫名稱尋找 Notion database，並自動建立一個 `__NDM_INDEX__` 的 number 欄位作為 row 順序依據，讓 `index` 操作可以固定從 `1` 開始。這個內部欄位預設不會出現在一般匯出 JSON 裡。

## 安裝

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .
```

## 使用方式

若未提供 `--token` 或 `--database-name`，程式會在執行時互動輸入。

如果你會重複操作同一個資料庫，建議在專案根目錄建立 `.env`:

```dotenv
NOTION_DB_MANAGER_TOKEN=secret_xxx
NOTION_DB_MANAGER_DATABASE_NAME=Tasks
```

之後就可以省略這兩個參數:

```bash
notion-db-manager reader export-all --output all.json
```

所有相對路徑的 JSON 輸入輸出都會統一走專案根目錄下的 `output/`。
例如 `--output all.json` 實際會寫到 `output/all.json`；
`--input all.json` 也會優先從 `output/all.json` 讀取。

參數優先順序是:

1. 命令列參數 `--token` / `--database-name`
2. 作業系統環境變數或 `.env`
3. 執行時互動輸入

支援的環境變數名稱:

1. `NOTION_DB_MANAGER_TOKEN`
2. `NOTION_DB_MANAGER_DATABASE_NAME`
3. `NOTION_TOKEN`
4. `NOTION_DATABASE_NAME`

### Reader

完整匯出:

```bash
notion-db-manager reader export-all --token "secret_xxx" --database-name "Tasks" --output all.json
```

只匯出指定欄位:

```bash
notion-db-manager reader export-columns --token "secret_xxx" --database-name "Tasks" --columns Name Status Score --output columns.json
```

只匯出指定 row:

```bash
notion-db-manager reader export-rows --token "secret_xxx" --database-name "Tasks" --rows 1,3,5-7 --output rows.json
```

### Writer

把 `export-all` 的 JSON append 到現有資料庫:

```bash
notion-db-manager writer import-full --token "secret_xxx" --database-name "Tasks" --input all.json --mode append
```

先清空資料庫再匯入 `export-all` 的 JSON:

```bash
notion-db-manager writer import-full --token "secret_xxx" --database-name "Tasks" --input all.json --mode replace
```

從指定 index 開始覆蓋指定欄位；如果超出既有 row 數，會自動新增新 page:

```bash
notion-db-manager writer write-columns --token "secret_xxx" --database-name "Tasks" --input columns.json --start-index 3
```

新增 row 到最後:

```bash
notion-db-manager writer write-rows --token "secret_xxx" --database-name "Tasks" --input rows.json --mode append
```

在指定 index 插入 row，後面的資料順位往後移:

```bash
notion-db-manager writer write-rows --token "secret_xxx" --database-name "Tasks" --input rows.json --mode insert --index 3
```

從指定 index 開始覆蓋既有 row，不會新增新 page:

```bash
notion-db-manager writer write-rows --token "secret_xxx" --database-name "Tasks" --input rows.json --mode overwrite --index 3
```

## JSON 格式

三種 Reader 都輸出同樣的外層格式:

```json
{
  "meta": {
    "database_id": "...",
    "database_name": "Tasks",
    "export_type": "full",
    "selected_columns": [],
    "selected_rows": [],
    "order_property": "__NDM_INDEX__",
    "exported_at": "2026-03-16T00:00:00+00:00"
  },
  "rows": [
    {
      "index": 1,
      "page_id": "...",
      "properties": {
        "Name": {"type": "title", "value": "Task A"},
        "Status": {"type": "status", "value": "Todo"},
        "Score": {"type": "number", "value": 10}
      }
    }
  ]
}
```

`write-columns` 可以直接吃 `export-columns` 產出的檔案。

`write-rows` 可以直接吃 `export-rows` 產出的檔案。

`import-full` 會直接吃 `export-all` 產出的檔案。

## 注意事項

1. Notion API 本身沒有穩定的資料列插入順位 API，所以本工具會以 `__NDM_INDEX__` 維護順序。
2. `replace` 模式是把原有 page archive 後再重建新資料，不是把 archive 的 page 復用。
3. `overwrite` row 模式會把該 row 的可寫欄位改成新資料；未提供的可寫欄位會清空。
4. 公式、rollup、created time 這類唯讀欄位會匯出，但寫入時會自動忽略。

## 專案結構 (Clean Architecture)

```text
output/                             # 統一收斂 JSON 輸入輸出
notion_db_manager/
├── core/                           # 核心基底 (例外階層、環境配置、通用型別)
│   ├── config.py
│   ├── exceptions.py
│   └── types.py
├── domain/                         # 領域層 (純商業邏輯與富領域模型)
│   ├── models/                     # Database, Page, Document 實體
│   │   ├── database.py
│   │   ├── document.py
│   │   └── page.py
│   ├── properties/                 # 多型屬性策略系統 (PropertyValue & Registry)
│   │   ├── base.py
│   │   ├── file.py
│   │   ├── number.py
│   │   ├── primitive.py
│   │   ├── readonly.py
│   │   ├── registry.py
│   │   ├── relation.py
│   │   ├── select.py
│   │   └── text.py
│   └── validation.py               # 領域驗證 (列索引表達式解析等)
├── application/                    # 應用層 (Command 模式與介面抽象)
│   ├── commands/                   # 各項獨立功能抽象 (Use Cases)
│   │   ├── base.py
│   │   ├── export_all.py
│   │   ├── export_columns.py
│   │   ├── export_rows.py
│   │   ├── import_full.py
│   │   ├── write_columns.py
│   │   └── write_rows.py
│   └── interfaces/                 # 依賴反轉介面 (Ports)
│       ├── document_storage.py
│       └── notion_gateway.py
├── infrastructure/                 # 基礎設施層 (具體實作 Adapters)
│   ├── notion/                     # Notion API 通訊與轉換
│   │   ├── client.py
│   │   ├── gateway.py
│   │   └── mappers.py
│   └── storage/                    # 檔案儲存與路徑解析
│       ├── json_storage.py
│       └── path_resolver.py
└── cli/                            # 命令列介面層 (CLI Presentation)
    ├── dispatch.py                 # 命令分派與相依注入
    ├── main.py                     # CLI 總進入點
    ├── parser.py                   # 參數解析構建
    └── prompt.py                   # 終端互動輸入提示
```