#!/usr/bin/env python
# -*- coding: utf-8 -*-
import MeCab

import conf.config_archiver as config
from base_analyzer import BaseAnalyzer

# 参考サイト：https://taku910.github.io/mecab/


class MecabAnalyzer(BaseAnalyzer):
    """
    Mecabを使って解析するクラス
    """
    def __init__(self):
        super().__init__()

        # 設定ファイルにMecabのシステム辞書が設定されていればそれを使い、そうでなければデフォルトの辞書で動作させる。
        if config.MECAB_USER_DICT:
            self.tagger = MeCab.Tagger('-Ochasen -d ' + config.MECAB_USER_DICT)
        else:
            self.tagger = MeCab.Tagger('-Ochasen')


class Morpheme(object):
    """
    形態素の情報を格納するコンテナクラス
    """

    def __init__(self, word: str, part: str, original: str, polarity: float = 0.0):
        """
        :param word:
        :param part:
        :param original:
        :param polarity:
        """
        self.word = word
        self.part_of_speech = part
        self.original_form = original
        self.polarity = polarity
