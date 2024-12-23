from flask import Flask, request, abort
from dotenv import load_dotenv
import os
from linebot import WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent
)

# 自定義功能模組
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

# 驗證環境變數
if not channel_access_token or not channel_secret:
    raise ValueError("環境變數 'channel_access_token' 或 'channel_secret' 未正確配置！")

# 初始化 LINE Bot API 和 WebhookHandler
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)
handler = WebhookHandler(channel_secret)

from flask import Flask, request, abort
from dotenv import load_dotenv
import os
import logging
from linebot import WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage
)

# 自定義功能模組（請確保這些模組存在且可正常運行）
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

# 初始化 LINE Bot API 和 WebhookHandler
line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

# 使用者狀態記錄
user_states = {}

# 路由設定
@app.route("/")
def home():
    return "Webhook Running!!!"

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取簽名
    signature = request.headers.get('X-Line-Signature')

    # 獲取請求的正文
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 驗證簽名並處理事件
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()
    logging.info(f"Received message: {msg} from user: {user_id} with reply token: {event.reply_token}")

    try:
        # 根據使用者狀態進行處理
        if user_id in user_states and user_states[user_id] == 'waiting_for_keywords':
            handle_keywords_input(event, msg, user_id)
        elif user_id in user_states and user_states[user_id] == 'waiting_for_stock':
            result2 = create_stock_message(msg)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=result2)
            )
            user_states[user_id] = None
        elif user_id in user_states and user_states[user_id] == 'waiting_for_backtest':
            result1 = backtest(msg)
            formatted_result = format_backtest_result(result1)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=formatted_result)
            )
            user_states[user_id] = None
        else:
            handle_regular_message(event, msg, user_id)
    except Exception as e:
        logging.error(f"Error handling webhook: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="發生錯誤，請稍後再試。")
        )
        user_states[user_id] = None

def handle_keywords_input(line_bot_api, event, msg, user_id):
    keywords = [keyword.strip() for keyword in msg.split(',') if keyword.strip()]
    if keywords:
        logging.info(f"Fetching news for keywords: {keywords}")
        message = fetch_and_filter_news_message(keywords, limit=10)

        if isinstance(message, TextMessage):
            logging.info(f"Fetched news: {message.text[:100]}...")  # Log first 100 chars of the text
            reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        else:
            message_str = str(message)
            logging.info(f"Fetched news: {message_str[:100]}...")  # Log first 100 chars
            reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[TextMessage(text=message_str)])

        line_bot_api.reply_message(reply_message)
    else:
        prompt_message = TextMessage(text="請輸入有效的關鍵字，用逗號分隔:")
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[prompt_message])
        line_bot_api.reply_message(reply_message)

def handle_regular_message(line_bot_api, event, msg, user_id):
    if '財報' in msg:
        message = buttons_message1()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)
    elif '基本股票功能' in msg:
        message = buttons_message1()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)
        return
    elif '換股' in msg:
        message = buttons_message2()
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)
        return
    elif '目錄' in msg:
        carousel = Carousel_Template()
        logging.info(f"Carousel_Template 返回的消息: {carousel}")
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[carousel])
        line_bot_api.reply_message(reply_message)
        return
    elif '新聞' in msg:
        message = TextMessage(text="請輸入關鍵字，用半形逗號分隔:")
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)
        user_states[user_id] = 'waiting_for_keywords'
        return
    elif '查詢即時開盤價跟收盤價' in msg:
        message = TextMessage(text="請輸入股票代號:")
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)
        user_states[user_id] = 'waiting_for_stock'
        return
    elif '回測' in msg:
        message = TextMessage(text="請問要回測哪一支,定期定額多少,幾年(請用半形逗號隔開):")
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)
        user_states[user_id] = 'waiting_for_backtest'
        return


def format_backtest_result(result):
    result_str = str(result)
    start = result_str.find("text='") + 6
    end = result_str.rfind("'")
    content = result_str[start:end]
    formatted_result = content.replace("\\n", "\n")
    return formatted_result

@handler.add(MemberJoinedEvent)
def welcome(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        uid = event.joined.members[0].user_id
        gid = event.source.group_id
        profile = line_bot_api.get_group_member_profile(gid, uid)
        name = profile.display_name
        message = TextMessage(text=f'{name}歡迎加入')
        reply_message = ReplyMessageRequest(reply_token=event.reply_token, messages=[message])
        line_bot_api.reply_message(reply_message)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=port)
