# 如何生成架構圖圖片

## 方法 1: 在線工具（推薦）

### Mermaid Live Editor
1. 訪問：https://mermaid.live/
2. 複製 `ARCHITECTURE.md` 中的 mermaid 代碼
3. 粘貼到編輯器中
4. 點擊 "Export" → 選擇 PNG/SVG/PDF

### 其他在線工具
- https://mermaid.ink/ - 直接生成圖片 URL
- https://kroki.io/ - 支援多種圖表格式

## 方法 2: 使用 Mermaid CLI（命令行）

### 安裝
```bash
npm install -g @mermaid-js/mermaid-cli
```

### 生成圖片
```bash
# 從單個 mermaid 文件生成
mmdc -i diagram.mmd -o diagram.png

# 從 markdown 文件中提取並生成
mmdc -i ARCHITECTURE.md -o architecture.png
```

## 方法 3: VS Code 插件

### 安裝插件
1. 打開 VS Code
2. 搜索並安裝 "Mermaid Preview" 或 "Markdown Preview Mermaid Support"
3. 打開 `ARCHITECTURE.md`
4. 右鍵 → "Export to PNG/SVG"

## 方法 4: 在 GitHub 上查看（自動渲染）

當您推送到 GitHub 後，圖表會自動渲染：
- 訪問：https://github.com/Riven-dev1030/ansible_network-lab/blob/main/ARCHITECTURE.md
- 圖表會自動顯示為可視化圖形

## 方法 5: 使用本地服務器預覽

```bash
# 安裝 Markdown 預覽工具
pip install grip

# 啟動預覽服務器
grip ARCHITECTURE.md

# 訪問 http://localhost:6419 查看渲染後的圖表
```

## 快速預覽鏈接（Mermaid Ink）

以下是使用 mermaid.ink 的直接圖片 URL 示例：

```
https://mermaid.ink/img/[Base64編碼的Mermaid代碼]
```

您可以直接在瀏覽器中打開這些鏈接查看圖片。
