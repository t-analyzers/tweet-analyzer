import re

import MeCab
import numpy as np

from shared.datetime_extentions import *
from shared.mongo_wrapper import *
from shared.morpheme import Morpheme
from shared.log import Log
import config as config

# coding=utf-8
# write code...


class MecabEvaluator(object):
    """
    Mecabを用いてテキストのネガポジ分析を行うクラス
    今のところ精度はゴミ！！
    """

    def __init__(self):
        # Mecabのシステム辞書が設定されていればそれを使い、そうでなければデフォルトの辞書で動作させる。
        if config.MECAB_SYS_DICT:
            self.tagger = MeCab.Tagger('-d ' + config.MECAB_SYS_DICT)
        else:
            self.tagger = MeCab.Tagger('-Ochasen')

        self.PN_DICT = self.__init_pn_dict()
        self.__log = Log("mecab_evaluator")

    def set_negaposi_score(self, start_datetime: datetime, end_datetime: datetime,):
        """
        ネガポジスコアを算出し、MongoDBにセットする。
        リツィート/スパムは対象外。
        :param start_datetime: 検索開始時刻
        :param end_datetime: 検索終了時刻
        :return: なし
        """
        self.__log.info("ネガポジスコアの算出開始")
        # リツィート/スパムは除外、過去14日分を対象

        search_condition = {'retweeted_status': {'$eq': None}, 'spam': {'$eq': None},
                            'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}

        # ネガポジスコアを算出し、DBにセットする
        tweets = MongoWrapper.connect_tweets()
        for tweet in tweets.find(search_condition, {'id': 1, 'text': 1}):
            score = self.negaposi_by_pn_dict(tweet["text"])
            tweets.update({'_id': tweet['_id']}, {'$set': {'negaposi': score}})
            # print("text: {}".format(tweet["text"]))
            # print("score: {}".format(score))
        self.__log.info("ネガポジスコアの算出完了")

    def negaposi_by_pn_dict(self, text: str) -> float:
        """
        単語感情極性対応表を使って極性値の平均を算出する。
        :param text:文字列
        :return:平均極性値（-1〜1）
        """
        polarity_list = []
        # 1文ごとに分割し、httpで始まるものは除外したうえで処理を行う。
        sentences = [s for s in re.split(r'\s+|。|．|？', text) if len(s) > 0 and not s.startswith("http")]
        for sentence in sentences:
            m_list = self._sentence2morpheme_list(sentence=sentence)

            for idx, m in enumerate(m_list):
                prev = m_list[idx - 1]
                # 動詞・形容詞直後に強い肯定or否定が続く場合、極性値を0にして調整する。
                # おそらくCaboChaを使って係り受け解析をするのがよりよい方法と思われる。
                if prev and (abs(m.polarity) > -0.9) and (prev.part_of_speech in ("動詞", "形容詞")):
                    prev.pn_polarity = 0.0

            # 極性値がニュートラルな（どちらでもない）ものは除外する。
            # 現状、ネガティブに偏ってしまっているので適当に調整している。
            polarity_list.extend([m.polarity for m in m_list
                                  if m.part_of_speech in ("形容詞", "動詞", "助詞") and (m.polarity < -0.5 or m.polarity > 0.0)])
            """
            polarity_list.extend([m.polarity for m in m_list
                                  if (abs(m.polarity) > 0.8 and m.part_of_speech != "名詞") or (abs(m.polarity) > 0.5)])
            """

        if len(polarity_list) > 0:
            return np.array(polarity_list).mean()
        else:
            return 0.0

    def _sentence2morpheme_list(self, sentence: str) -> list:
        """
        文をMecabで分割し、形態素データのリストに変換する。
        :param sentence:文
        :return:文から生成したMorphemeオブジェクトのリスト
        """
        morpheme_list = []
        self.tagger.parse("")
        node = self.tagger.parseToNode(sentence)

        while node:
            morpheme = Morpheme(node=node, pn_dict=self.PN_DICT)

            # 記号などは算出対象（リスト）に含めないようにする。
            if morpheme.part_of_speech != "BOS/EOS" and morpheme.part_of_speech != "記号":
                morpheme_list.append(morpheme)

            node = node.next

        return morpheme_list

    @staticmethod
    def __init_pn_dict() -> dict:
        """
        単語感情極性表を辞書形式に変換する。
        :return: dict key: タプル(単語, 品詞) value: 極性値
        """
        pn_dict = {}
        with open("conf/pn_ja.dic", "r", encoding="shift-jis") as file:
            for idx, text in enumerate(file):
                l = text.strip().split(":")
                key = (l[0], l[2])
                val = float(l[3])
                pn_dict[key] = val
        return pn_dict
