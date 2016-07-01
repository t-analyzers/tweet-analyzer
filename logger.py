import logging
from logging.handlers import TimedRotatingFileHandler

# coding=utf-8
# write code...


class Log:
    def __init__(self, log_type):
        # ロガーオブジェクトの作成
        logger = logging.getLogger(log_type)
        # ログレベルの設定
        logger.setLevel(logging.DEBUG)
        # ハンドラの設定
        handler = TimedRotatingFileHandler(filename="./logs/tweet-analyzer.log", when="D", backupCount=30)
        # ログフォーマットの設定
        formatter = logging.Formatter("[%(asctime)s] %(name)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        # ロガーにハンドラを登録
        logger.addHandler(handler)
        self.logger = logger

    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.logger.exception(msg, *args, exc_info, **kwargs)
