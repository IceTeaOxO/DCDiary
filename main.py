import discord
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime
# import ollama
import requests
import json


# 加載 .env 文件
load_dotenv()

# 從環境變量中讀取 TOKEN
TOKEN = os.getenv("DISCORD_TOKEN")
DOWNLOAD_FOLDER = 'attachments'
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://192.168.0.19:11434/api/chat")

# 連接到SQLite資料庫
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

# 建立聊天記錄表格，新增 location 欄位
c.execute('''CREATE TABLE IF NOT EXISTS chat_logs
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user TEXT, 
                message TEXT, 
                file_path TEXT,
                file_type TEXT,
                location TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

# 創建 intents 實例
intents = discord.Intents.default()
intents.messages = True  # 啟用接收消息事件
intents.message_content = True  # 啟用接收消息內容事件（需要在 Discord 開發者門戶啟用）



# 初始化Discord客戶端
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

@client.event
async def on_message(message):
    # 忽略來自bot自己的訊息
    if message.author == client.user:
        return

    # 確保下載資料夾存在
    if not os.path.exists(DOWNLOAD_FOLDER):
        os.makedirs(DOWNLOAD_FOLDER)

    # 獲取群組或頻道名稱
    location = str(message.channel)  # 獲取頻道名稱

    if message.attachments:
        for attachment in message.attachments:
            # 下載檔案，並在檔名後添加當前日期
            current_date = datetime.now().strftime('%Y%m%d')  # 格式化日期
            file_name, file_extension = os.path.splitext(attachment.filename)
            new_file_name = f"{file_name}_{current_date}{file_extension}"
            file_path = os.path.join(DOWNLOAD_FOLDER, new_file_name)
            await attachment.save(file_path)

            # 獲取檔案類型
            file_type = attachment.content_type if attachment.content_type else 'unknown'

            # 將聊天記錄和檔案路徑插入資料庫
            c.execute("INSERT INTO chat_logs (user, message, file_path, file_type, location) VALUES (?, ?, ?, ?, ?)", 
                      (str(message.author), message.content, file_path, file_type, location))
            conn.commit()
            print(f"Message from {message.author}: {message.content} with file {file_path} of type {file_type} from {location}")
    else:
        # 將聊天記錄插入資料庫
        c.execute("INSERT INTO chat_logs (user, message, file_path, file_type, location) VALUES (?, ?, ?, ?, ?)",
                  (str(message.author), message.content, None, None, location))
        conn.commit()
        print(f"Message from {message.author}: {message.content} from {location}")
        # 處理指令

    if message.content.startswith("/t "):
        question = message.content[3:]  # 獲取指令後的問題
        await handle_ollama_response(OLLAMA_URL, "請將下列的句子翻譯成意思相同的英文句子、日文句子以及日文句子的發音，其他字詞使用繁體中文回答，除此之外不要給我其他資訊：" + question, message.channel)

    if message.content.startswith("/c "):
        question = message.content[3:]  # 獲取指令後的問題
        await handle_ollama_response(OLLAMA_URL, question, message.channel)

async def handle_ollama_response(url, question, channel):
    # 發送請求
    response = requests.post(url, json={
        "model": "gemma2:2b",
        "messages": [
            {"role": "user", "content": question}
        ]
    }, stream=True)

    # 檢查響應狀態碼
    if response.status_code == 200:
        messages = []  # 用於收集內容的列表

        # 逐行處理響應
        for line in response.iter_lines():
            if line:
                try:
                    # 解碼並解析JSON數據
                    data = json.loads(line.decode('utf-8'))
                    if 'message' in data and 'content' in data['message']:
                        messages.append(data['message']['content'])  # 收集內容
                    if data.get('done', False):  # 檢查是否完成
                        break
                except json.JSONDecodeError:
                    print("JSON Decode Error: ", line)

        # 合併所有內容並發送
        full_message = ''.join(messages)
        if len(full_message) > 2000:
            # 如果消息太長，則分割發送
            for i in range(0, len(full_message), 2000):
                await channel.send(full_message[i:i + 2000])
        else:
            await channel.send(full_message)
    else:
        await channel.send("無法獲取響應，請稍後再試。")



client.run(TOKEN)
