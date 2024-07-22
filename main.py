import discord
import sqlite3
import os
from dotenv import load_dotenv

# 加載 .env 文件
load_dotenv()

# 從環境變量中讀取 TOKEN
TOKEN = os.getenv("DISCORD_TOKEN")
DOWNLOAD_FOLDER = 'attachments'

# 連接到SQLite資料庫
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

# 建立聊天記錄表格，擴展以支持不同類型的檔案
c.execute('''CREATE TABLE IF NOT EXISTS chat_logs
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user TEXT, 
                message TEXT, 
                file_path TEXT,
                file_type TEXT)''')

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

    if message.attachments:
        for attachment in message.attachments:
            # 下載檔案
            file_path = os.path.join(DOWNLOAD_FOLDER, attachment.filename)
            await attachment.save(file_path)

            # 獲取檔案類型
            file_type = attachment.content_type if attachment.content_type else 'unknown'

            # 將聊天記錄和檔案路徑插入資料庫
            c.execute("INSERT INTO chat_logs (user, message, file_path, file_type) VALUES (?, ?, ?, ?)", 
                      (str(message.author), message.content, file_path, file_type))
            conn.commit()
            print(f"Message from {message.author}: {message.content} with file {file_path} of type {file_type}")
    else:
        # 將聊天記錄插入資料庫
        c.execute("INSERT INTO chat_logs (user, message, file_path, file_type) VALUES (?, ?, ?, ?)",
                  (str(message.author), message.content, None, None))
        conn.commit()
        print(f"Message from {message.author}: {message.content}")

client.run(TOKEN)
