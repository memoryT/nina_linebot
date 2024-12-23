from flask import Flask, request, abort
from linebot import WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, 
    MemberJoinedEvent, TemplateSendMessage
)
from message import *
from dotenv import load_dotenv
import os
import logging
from enum import Enum
from typing import Dict
from stock import *
from csv import *
import datetime as dt
from data import *
from news import *

# Initialize Flask and logging
app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
channel_access_token = os.getenv('channel_access_token')
channel_secret = os.getenv('channel_secret')

if not channel_access_token or not channel_secret:
    raise ValueError("Missing LINE Bot credentials in environment variables")

# Initialize LINE Bot API
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# User states storage
user_states = {}

class UserState(Enum):
    WAITING_FOR_KEYWORDS = "waiting_for_keywords"
    WAITING_FOR_STOCK = "waiting_for_stock"
    WAITING_FOR_BACKTEST = "waiting_for_backtest"

def send_message(reply_token: str, text: str):
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text=text)
    )

def send_template(reply_token: str, template):
    line_bot_api.reply_message(
        reply_token,
        TemplateSendMessage(
            alt_text="Template message",
            template=template
        )
    )

@app.route("/")
def home():
    return "Webhook Running!!!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    logger.info("Request body: %s", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    logger.info(f"Message from {user_id}: {msg}")

    try:
        if user_id in user_states:
            handle_state_based_input(event, msg, user_id)
        else:
            handle_regular_message(event, msg, user_id)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        send_message(event.reply_token, "處理請求時發生錯誤，請稍後再試。")
        user_states.pop(user_id, None)

def handle_state_based_input(event, msg: str, user_id: str):
    state = user_states.get(user_id)
    if state == UserState.WAITING_FOR_KEYWORDS.value:
        handle_keywords_input(event, msg, user_id)
    elif state == UserState.WAITING_FOR_STOCK.value:
        result = create_stock_message(msg)
        send_message(event.reply_token, result)
  
    
    user_states.pop(user_id, None)

def handle_regular_message(event, msg: str, user_id: str):
    try:
        if '財報' in msg or '基本股票功能' in msg:
            send_template(event.reply_token, buttons_message1())
        elif '換股' in msg:
            send_template(event.reply_token, buttons_message2())
        elif '目錄' in msg:
            carousel = Carousel_Template()
            send_template(event.reply_token, carousel)
        elif '新聞' in msg:
            send_message(event.reply_token, "請輸入關鍵字，用半形逗號分隔:")
            user_states[user_id] = UserState.WAITING_FOR_KEYWORDS.value
        elif '查詢即時開盤價跟收盤價' in msg:
            send_message(event.reply_token, "請輸入股票代號:")
            user_states[user_id] = UserState.WAITING_FOR_STOCK.value
    except Exception as e:
        logger.error(f"Error in handle_regular_message: {str(e)}")
        send_message(event.reply_token, "請求時發生錯誤，請稍後再試。")

def send_template(reply_token: str, template):
    if template is None:
        logger.error("The template is empty or None.")
        send_message(reply_token, "發生錯誤，請稍後再試。")
        return

    try:
        line_bot_api.reply_message(
            reply_token,
            template
        )
    except Exception as e:
        logger.error(f"Error sending template: {str(e)}")
        send_message(reply_token, "處理模板時發生錯誤，請稍後再試。")

def handle_keywords_input(event, msg: str, user_id: str):
    # 假設輸入格式為 "關鍵字1,關鍵字2"
    keywords = msg.split(',')
    # 去除空格
    keywords = [keyword.strip() for keyword in keywords]
    
    if not keywords:
        send_message(event.reply_token, "請輸入有效的關鍵字，用半形逗號分隔。")
        return

    try:
        # 查詢並篩選新聞
        news_message = fetch_and_filter_news_message(keywords)
        send_message(event.reply_token, news_message.text)
    except Exception as e:
        logger.error(f"Error handling keywords input: {str(e)}")
        send_message(event.reply_token, "處理關鍵字時發生錯誤，請稍後再試。")
        

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)