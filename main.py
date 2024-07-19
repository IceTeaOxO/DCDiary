import discord
import sqlite3
import os

# 替換成您的Discord bot token
TOKEN = 'your_discord_bot_token_here'

  # 連接到SQLite資料庫
conn = sqlite3.connect('chat_history.db')
c = conn.cursor()

  # 建立聊天記錄表格
c.execute('''CREATE TABLE IF NOT EXISTS chat_logs
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user TEXT, 
                message TEXT, 
                image_path TEXT)''')

  # 初始化Discord客戶端
client = discord.Client()

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
      # 如果沒有圖片附件
      else:
          # 將聊天記錄插入資料庫
          c.execute("INSERT INTO chat_logs (user, message, image_path) VALUES (?, ?, ?)",
                   (str(message.author), message.content, None))
          conn.commit()

client.run(TOKEN)