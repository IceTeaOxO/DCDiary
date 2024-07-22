import discord
import sqlite3
import os
from dotenv import load_dotenv

# 加載 .env 文件
load_dotenv()

# 從環境變量中讀取 TOKEN
TOKEN = os.getenv("DISCORD_TOKEN")

  # 連接到SQLite資料庫
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

  # 建立聊天記錄表格
c.execute('''CREATE TABLE IF NOT EXISTS chat_logs
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user TEXT, 
                message TEXT, 
                image_path TEXT)''')

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

      # 如果有圖片附件
      if message.attachments:
          for attachment in message.attachments:
              # 下載圖片
              image_path = f'images/{attachment.filename}'
              await attachment.save(image_path)

              # 將聊天記錄和圖片路徑插入資料庫
              c.execute("INSERT INTO chat_logs (user, message, image_path) VALUES (?, ?, ?)", 
                       (str(message.author), message.content, image_path))
              conn.commit()
              print(f"Message from {message.author}: {message.content} with image {image_path}")
      # 如果沒有圖片附件
      else:
          # 將聊天記錄插入資料庫
          c.execute("INSERT INTO chat_logs (user, message, image_path) VALUES (?, ?, ?)",
                   (str(message.author), message.content, None))
          conn.commit()
          print(f"Message from {message.author}: {message.content}")

client.run(TOKEN)