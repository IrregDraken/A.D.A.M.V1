from threading import Thread

from app import app
from adam_bot import run_bot
from button_handler import run_button_handler
from bots_command import run_auto_responder


def start_flask():
    app.run(host="0.0.0.0", port=10000)


def start_telegram_bot():
    run_bot()


def start_button_handler():
    run_button_handler()


def start_auto_responder():
    run_auto_responder()


if __name__ == "__main__":

    bot_thread = Thread(
        target=start_telegram_bot,
        daemon=True
    )

    button_thread = Thread(
        target=start_button_handler,
        daemon=True
    )

    auto_thread = Thread(
        target=start_auto_responder,
        daemon=True
    )

    bot_thread.start()
    button_thread.start()
    auto_thread.start()

    start_flask()