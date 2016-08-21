#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from logging.handlers import TimedRotatingFileHandler
import os


class Log:
    def __init__(self, log_type):
        # ロガーオブジェクトの作成
        logger = logging.getLogger(log_type)
        # ログレベルの設定
        logger.setLevel(logging.DEBUG)
        # ハンドラの設定
        log_file_name = os.path.abspath("../logs/tweet-analyzer.log")
        handler = TimedRotatingFileHandler(filename=log_file_name, when="D", backupCount=30)
        # ログフォーマットの設定
        formatter = logging.Formatter("[%(asctime)s] %(name)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        # ロガーにハンドラを登録
        logger.addHandler(handler)
        self.__logger = logger

    def info(self, msg, *args, **kwargs):
        self.__logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.__logger.debug(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.__logger.error(msg, *args, **kwargs)

    def exception(self, msg, *args, exc_info=True, **kwargs):
        self.__logger.exception(msg, *args, exc_info, **kwargs)
