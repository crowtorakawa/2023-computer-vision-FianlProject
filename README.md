# 2023-computer-vision-FianlProject
#  Flask 相機偵測系統

## 功能說明

### 1. 首頁 (`/`)
- 顯示相機串流影像  
- 提供控制按鈕：
  - **Start/Stop**：開啟或關閉相機  
  - **Capture**：截圖並儲存  
  - **Detect**：啟動 YOLO 模型進行偵測  
<img width="300" height="300" alt="shot_01" src="https://github.com/user-attachments/assets/f355c6d5-55b5-4b28-9665-5451804be963" />

---

### 2. 影像串流 (`/video_feed`)
- 使用 `gen_frames()` 持續讀取相機影像，轉換成 JPEG 格式後串流到前端 `<img>`。  
- 若相機斷線，會自動等待並重試。  
<img width="540" height="73" alt="image" src="https://github.com/user-attachments/assets/0074096f-d324-4854-8266-47e06d745ab0" />

---

### 3. 控制請求 (`/requests`)
- 接收前端按鈕送出的指令 (`Start/Stop` / `Capture` / `Detect`)。  
- 操作流程：
  - **Stop** → 釋放相機資源  
  - **Start** → 重新開啟相機  
  - **Capture** → 儲存圖片到指定資料夾  
  - **Detect** → 啟動 YOLO 模型進行影像辨識，將結果存入 MongoDB  
<img width="705" height="114" alt="image" src="https://github.com/user-attachments/assets/a28fe3e5-57db-407c-ad02-ed9eb68b7dcc" />

---

### 4. 偵測結果紀錄 (`/log`)
- 從 MongoDB 讀取已存入的偵測結果  
- 顯示在頁面上，以表格或列表方式呈現  
<img width="1066" height="448" alt="image" src="https://github.com/user-attachments/assets/44d49599-0f36-4dfb-a098-b3417b0746c3" />

---

##  技術架構

- **後端框架**：Flask  
- **前端**：Jinja2 模板 + Bootstrap  
- **影像處理**：OpenCV  
- **物件偵測**：YOLO 模型  
- **資料庫**：MongoDB (儲存偵測 log)  

---

##  程式流程

1. 進入首頁 `/` → 顯示相機影像串流  
2. 使用者可操作控制按鈕：  
   - 開啟/關閉相機  
   - 截圖  
   - 啟動偵測  
3. 偵測結果會寫入 MongoDB  
4. 使用者可至 `/log` 查看歷史紀錄  

---

## 系統架構圖

```mermaid
flowchart LR
    Browser((瀏覽器)) -->|HTTP 請求| Flask
    Flask -->|讀取影像| Camera[相機]
    Flask -->|偵測| YOLO[YOLO 模型]
    Flask -->|存取紀錄| MongoDB[(MongoDB)]
    Flask -->|串流影像/結果| Browser
