from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import logging
from linebot import WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent
)

# 自定義模組（請確保這些模組存在且可正常運行）
from data import *
from message import *
from news import *
from Function import *
from stock import *

# 加載環境變數
load_dotenv()

# 初始化 Flask 應用
app = Flask(__name__)

# 從環境變數中讀取 LINE Bot 資訊
channel_access_token = os.getenv('channel_access_token')
channel_secret = os.getenv('channel_secret')
port = int(os.getenv('PORT', 5000))

# 驗證環境變數是否正確
if not channel_access_token or not channel_secret:
    raise ValueError("環境變數 'channel_access_token' 或 'channel_secret' 未正確配置！")

# 初始化 LINE Bot API 和 WebhookHandler
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# 使用者狀態記錄
user_states = {}

# 基本路由
@app.route("/")
def home():
    return "Webhook Running!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. 請檢查 channel_access_token 或 channel_secret 是否正確。")
        abort(400)

    return 'OK'

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    logging.info(f"接收到來自使用者 {user_id} 的訊息: {msg}")

    try:
        # 根據使用者狀態進行邏輯處理
        if user_states.get(user_id) == 'waiting_for_keywords':
            keywords = [keyword.strip() for keyword in msg.split(',') if keyword.strip()]
            if keywords:
                news_message = fetch_and_filter_news_message(keywords, limit=10)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=news_message))
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入有效的關鍵字（用逗號分隔）。"))
            user_states[user_id] = None
        elif user_states.get(user_id) == 'waiting_for_stock':
            stock_message = create_stock_message(msg)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=stock_message))
            user_states[user_id] = None
        elif user_states.get(user_id) == 'waiting_for_backtest':
            backtest_result = backtest(msg)
            formatted_result = format_backtest_result(backtest_result)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=formatted_result))
            user_states[user_id] = None
        else:
            # 預設回覆或功能選單
            default_reply = TextSendMessage(text="請選擇功能或輸入指令（例如：新聞、回測等）。")
            line_bot_api.reply_message(event.reply_token, default_reply)
    except Exception as e:
        logging.error(f"處理訊息時發生錯誤: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="發生錯誤，請稍後再試。"))

# 處理新成員加入事件
@handler.add(MemberJoinedEvent)
def welcome(event):
    try:
        joined_user_id = event.joined.members[0].user_id
        group_id = event.source.group_id
        profile = line_bot_api.get_group_member_profile(group_id, joined_user_id)
        welcome_message = f"歡迎 {profile.display_name} 加入！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=welcome_message))
    except Exception as e:
        logging.error(f"歡迎訊息處理失敗: {e}")

# 格式化回測結果
def format_backtest_result(result):
    try:
        content = str(result).replace("\\n", "\n")
        return content
    except Exception as e:
        logging.error(f"格式化回測結果時發生錯誤: {e}")
        return "回測結果格式化失敗。"

# 啟動 Flask 應用
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port)
