from flask import Flask, request, abort
from linebot import WebhookHandler, LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, MemberJoinedEvent, ReplyMessageRequest
from dotenv import load_dotenv
import os
import logging
from enum import Enum
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserState(Enum):
    WAITING_FOR_KEYWORDS = "waiting_for_keywords"
    WAITING_FOR_STOCK = "waiting_for_stock"
    WAITING_FOR_BACKTEST = "waiting_for_backtest"

class LineBotApp:
    def __init__(self):
        load_dotenv()
        self.validate_env()
        self.app = Flask(__name__)
        self.line_bot_api = LineBotApi(os.getenv('channel_access_token'))
        self.handler = WebhookHandler(os.getenv('channel_secret'))
        self.user_states: Dict[str, str] = {}
        self.setup_routes()
        self.setup_handlers()

    def validate_env(self):
        required_vars = ['channel_access_token', 'channel_secret']
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")

    def setup_routes(self):
        self.app.route("/")(self.home)
        self.app.route("/callback", methods=['POST'])(self.callback)

    def setup_handlers(self):
        @self.handler.add(MessageEvent, message=TextMessage)
        def handle_message(event):
            self.process_message(event)

        @self.handler.add(MemberJoinedEvent)
        def handle_member_joined(event):
            self.welcome_member(event)

    def home(self):
        return "Webhook Running!!!"

    def callback(self):
        signature = request.headers.get('X-Line-Signature')
        body = request.get_data(as_text=True)
        logger.info("Request body: %s", body)

        try:
            self.handler.handle(body, signature)
        except InvalidSignatureError:
            logger.error("Invalid signature")
            abort(400)

        return 'OK'

    def process_message(self, event):
        user_id = event.source.user_id
        msg = event.message.text.strip()
        logger.info("Message from %s: %s", user_id, msg)

        try:
            if user_id in self.user_states:
                self.handle_state_based_input(event, msg, user_id)
            else:
                self.handle_regular_message(event, msg, user_id)
        except Exception as e:
            logger.error("Error processing message: %s", str(e))
            self.send_error_message(event.reply_token)
            self.user_states.pop(user_id, None)

    def handle_state_based_input(self, event, msg: str, user_id: str):
        state = self.user_states.get(user_id)
        handlers = {
            UserState.WAITING_FOR_KEYWORDS.value: self.handle_keywords_input,
            UserState.WAITING_FOR_STOCK.value: self.handle_stock_input,
            UserState.WAITING_FOR_BACKTEST.value: self.handle_backtest_input
        }
        handler = handlers.get(state)
        if handler:
            handler(event, msg, user_id)
        self.user_states.pop(user_id, None)

    def handle_regular_message(self, event, msg: str, user_id: str):
        commands = {
            '財報': lambda: self.send_template(event.reply_token, buttons_message1()),
            '基本股票功能': lambda: self.send_template(event.reply_token, buttons_message1()),
            '換股': lambda: self.send_template(event.reply_token, buttons_message2()),
            '目錄': lambda: self.send_carousel(event.reply_token),
            '新聞': lambda: self.request_keywords(event.reply_token, user_id),
            '查詢即時開盤價跟收盤價': lambda: self.request_stock_code(event.reply_token, user_id),
            '回測': lambda: self.request_backtest_params(event.reply_token, user_id)
        }

        for cmd, handler in commands.items():
            if cmd in msg:
                handler()
                return

    def send_message(self, reply_token: str, text: str):
        self.line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)]
            )
        )

    def send_error_message(self, reply_token: str):
        self.send_message(reply_token, "處理請求時發生錯誤，請稍後再試。")

    def run(self, host='0.0.0.0', port=5000):
        self.app.run(host=host, port=port)

if __name__ == "__main__":
    bot = LineBotApp()
    port = int(os.getenv('PORT', 5000))
    bot.run(port=port)



