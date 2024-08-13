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
        await handle_ollama_response(OLLAMA_URL, "請將下列的句子翻譯成意思相同的英文和日文句子，日文請標註發音：" + question, message.channel)

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

    # 合併所有內容並發送
    full_message = ''.join(messages)
    if len(full_message) > 2000:
        # 如果消息太長，則分割發送
        for i in range(0, len(full_message), 2000):
            await channel.send(full_message[i:i + 2000])
    else:
        await channel.send(full_message)



client.run(TOKEN)
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:57.964937197Z","message":{"role":"assistant","content":"##"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.038188052Z","message":{"role":"assistant","content":"  "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.115895456Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.196239851Z","message":{"role":"assistant","content":"今天"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.278796018Z","message":{"role":"assistant","content":"天氣"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.360733148Z","message":{"role":"assistant","content":"真好"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.440418423Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.514349419Z","message":{"role":"assistant","content":" 的"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.602113772Z","message":{"role":"assistant","content":"翻譯"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.677528613Z","message":{"role":"assistant","content":"與"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.750506249Z","message":{"role":"assistant","content":"日"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.826601307Z","message":{"role":"assistant","content":"文"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.903158436Z","message":{"role":"assistant","content":"句子"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:58.978928593Z","message":{"role":"assistant","content":"\n\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.053265891Z","message":{"role":"assistant","content":"**"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.129409918Z","message":{"role":"assistant","content":"English"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.206500538Z","message":{"role":"assistant","content":":**"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.283125708Z","message":{"role":"assistant","content":" Today"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.364865791Z","message":{"role":"assistant","content":"'"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.442984242Z","message":{"role":"assistant","content":"s"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.521341814Z","message":{"role":"assistant","content":" weather"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.601131023Z","message":{"role":"assistant","content":" is"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.679105179Z","message":{"role":"assistant","content":" great"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.754250404Z","message":{"role":"assistant","content":"."},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.827616028Z","message":{"role":"assistant","content":" "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.90365405Z","message":{"role":"assistant","content":"\n\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:47:59.984159357Z","message":{"role":"assistant","content":"**"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.067973744Z","message":{"role":"assistant","content":"Japanese"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.141329313Z","message":{"role":"assistant","content":" ("},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.218338149Z","message":{"role":"assistant","content":"with"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.296137739Z","message":{"role":"assistant","content":" pronunciation"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.374180475Z","message":{"role":"assistant","content":"):"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.453511304Z","message":{"role":"assistant","content":"**"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.534907921Z","message":{"role":"assistant","content":"  "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.622551695Z","message":{"role":"assistant","content":"今日は"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.709544922Z","message":{"role":"assistant","content":"天気"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.792604681Z","message":{"role":"assistant","content":"いい"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.873798919Z","message":{"role":"assistant","content":"ですね"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:00.947774774Z","message":{"role":"assistant","content":"。"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.023979973Z","message":{"role":"assistant","content":" ("},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.099602137Z","message":{"role":"assistant","content":"Ky"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.174132651Z","message":{"role":"assistant","content":"ō"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.251453459Z","message":{"role":"assistant","content":" wa"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.328041835Z","message":{"role":"assistant","content":" ten"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.404519597Z","message":{"role":"assistant","content":"ki"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.48058997Z","message":{"role":"assistant","content":" i"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.5570169Z","message":{"role":"assistant","content":"-"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.634241929Z","message":{"role":"assistant","content":"i"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.710680456Z","message":{"role":"assistant","content":" desu"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.784870583Z","message":{"role":"assistant","content":" ne"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.860035194Z","message":{"role":"assistant","content":".)"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:01.935964883Z","message":{"role":"assistant","content":"\n\n\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.009616465Z","message":{"role":"assistant","content":"*"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.086249882Z","message":{"role":"assistant","content":" **"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.162381618Z","message":{"role":"assistant","content":"Explanation"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.237660872Z","message":{"role":"assistant","content":" of"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.311019865Z","message":{"role":"assistant","content":" the"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.385761759Z","message":{"role":"assistant","content":" pronunciation"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.462672407Z","message":{"role":"assistant","content":":**"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.535259559Z","message":{"role":"assistant","content":"\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.61101413Z","message":{"role":"assistant","content":"    "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.689077302Z","message":{"role":"assistant","content":"*"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.762752718Z","message":{"role":"assistant","content":" **"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.842373152Z","message":{"role":"assistant","content":"Ky"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:02.925973261Z","message":{"role":"assistant","content":"ō"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.008678219Z","message":{"role":"assistant","content":" wa"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.091227034Z","message":{"role":"assistant","content":"**:"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.164865662Z","message":{"role":"assistant","content":" Today"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.238319328Z","message":{"role":"assistant","content":"\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.315485705Z","message":{"role":"assistant","content":"    "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.391393701Z","message":{"role":"assistant","content":"*"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.466092401Z","message":{"role":"assistant","content":" **"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.538353963Z","message":{"role":"assistant","content":"ten"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.615740959Z","message":{"role":"assistant","content":"ki"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.692093263Z","message":{"role":"assistant","content":"**:"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.774263123Z","message":{"role":"assistant","content":" weather"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.848024753Z","message":{"role":"assistant","content":" "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:03.922613425Z","message":{"role":"assistant","content":"\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.005251086Z","message":{"role":"assistant","content":"    "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.083586391Z","message":{"role":"assistant","content":"*"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.15616019Z","message":{"role":"assistant","content":" **"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.230728129Z","message":{"role":"assistant","content":"i"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.30985438Z","message":{"role":"assistant","content":"**:"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.394493141Z","message":{"role":"assistant","content":" good"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.468466379Z","message":{"role":"assistant","content":","},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.543001505Z","message":{"role":"assistant","content":" is"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.619825339Z","message":{"role":"assistant","content":" "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.696367323Z","message":{"role":"assistant","content":"\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.771273219Z","message":{"role":"assistant","content":"    "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.846594988Z","message":{"role":"assistant","content":"*"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.919578717Z","message":{"role":"assistant","content":" **"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:04.995247297Z","message":{"role":"assistant","content":"i"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.069672114Z","message":{"role":"assistant","content":" desu"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.147030756Z","message":{"role":"assistant","content":" ne"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.22927084Z","message":{"role":"assistant","content":"**:"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.312372248Z","message":{"role":"assistant","content":"  "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.397327919Z","message":{"role":"assistant","content":"It"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.473650626Z","message":{"role":"assistant","content":"'"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.547784159Z","message":{"role":"assistant","content":"s"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.626392945Z","message":{"role":"assistant","content":" great"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.702136917Z","message":{"role":"assistant","content":"."},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.778465288Z","message":{"role":"assistant","content":"  "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.853853541Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:05.929803929Z","message":{"role":"assistant","content":"Des"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.005337702Z","message":{"role":"assistant","content":"u"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.079842058Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.154193849Z","message":{"role":"assistant","content":" means"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.229566444Z","message":{"role":"assistant","content":" \""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.305435498Z","message":{"role":"assistant","content":"is"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.37843731Z","message":{"role":"assistant","content":"\","},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.456994105Z","message":{"role":"assistant","content":" and"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.531395168Z","message":{"role":"assistant","content":"  "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.610416134Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.685504196Z","message":{"role":"assistant","content":"ne"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.760793283Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.834523333Z","message":{"role":"assistant","content":" at"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.911354536Z","message":{"role":"assistant","content":" the"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:06.986087557Z","message":{"role":"assistant","content":" end"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.064073535Z","message":{"role":"assistant","content":" expresses"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.140517144Z","message":{"role":"assistant","content":" a"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.213879646Z","message":{"role":"assistant","content":" polite"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.288722251Z","message":{"role":"assistant","content":" tone"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.362231479Z","message":{"role":"assistant","content":"\n\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.43870695Z","message":{"role":"assistant","content":" This"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.523170964Z","message":{"role":"assistant","content":" sentence"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.610373419Z","message":{"role":"assistant","content":" conveys"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.694335671Z","message":{"role":"assistant","content":" the"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.777714345Z","message":{"role":"assistant","content":" same"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.853032809Z","message":{"role":"assistant","content":" meaning"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:07.926831612Z","message":{"role":"assistant","content":" as"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.003496089Z","message":{"role":"assistant","content":" \""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.082097645Z","message":{"role":"assistant","content":"今天"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.160739304Z","message":{"role":"assistant","content":"天氣"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.237094841Z","message":{"role":"assistant","content":"真好"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.31394106Z","message":{"role":"assistant","content":"\""},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.390550585Z","message":{"role":"assistant","content":" in"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.466394685Z","message":{"role":"assistant","content":" Japanese"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.542415903Z","message":{"role":"assistant","content":"."},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.620077232Z","message":{"role":"assistant","content":"  "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.694919995Z","message":{"role":"assistant","content":"\n\n\n\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.771183018Z","message":{"role":"assistant","content":"Let"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.847583854Z","message":{"role":"assistant","content":" me"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:08.922894353Z","message":{"role":"assistant","content":" know"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.00753169Z","message":{"role":"assistant","content":" if"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.084705479Z","message":{"role":"assistant","content":" you"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.163107369Z","message":{"role":"assistant","content":" have"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.235865341Z","message":{"role":"assistant","content":" any"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.31641181Z","message":{"role":"assistant","content":" other"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.394527265Z","message":{"role":"assistant","content":" sentences"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.481117967Z","message":{"role":"assistant","content":" you"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.558761369Z","message":{"role":"assistant","content":"'"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.63814076Z","message":{"role":"assistant","content":"d"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.714608641Z","message":{"role":"assistant","content":" like"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.790461348Z","message":{"role":"assistant","content":" to"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.87016604Z","message":{"role":"assistant","content":" translate"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:09.954372261Z","message":{"role":"assistant","content":"!"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:10.042908094Z","message":{"role":"assistant","content":" 😊"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:10.129255791Z","message":{"role":"assistant","content":" "},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:10.207212977Z","message":{"role":"assistant","content":"\n"},"done":false}
# {"model":"gemma2:2b","created_at":"2024-08-13T13:48:10.283510023Z","message":{"role":"assistant","content":""},"done_reason":"stop","done":true,"total_duration":12484810798,"load_duration":30996110,"prompt_eval_count":35,"prompt_eval_duration":73755000,"eval_count":160,"eval_duration":12319771000}