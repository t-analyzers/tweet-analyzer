import re

import numpy as np

from mecab_analyzer import MecabAnalyzer, Morpheme
from shared.datetime_extentions import *
from shared.decorators import trace


# coding=utf-8
# write code...


class PnDictScorer(MecabAnalyzer):
    """
    日本語評価極性辞書を用いてネガポジ判定を行うクラス
    今のところ精度はゴミ！！
    """

    def __init__(self):
        super().__init__()
        self.PN_DICT = self._init_pn_dict()

    @trace()
    def update_negaposi(self, start_datetime: datetime, end_datetime: datetime):
        """
        ネガポジスコアを算出し、MongoDBにセットする。
        リツィート/スパムは対象外。
        :param start_datetime: 検索開始時刻
        :param end_datetime: 検索終了時刻
        :return: なし
        """
        self.log.info("ネガポジスコアの算出開始")
        # リツィート/スパムは除外、過去14日分を対象

        search_condition = {'retweeted_status': {'$eq': None}, 'spam': {'$eq': None},
                            'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}

        # ネガポジスコアを算出し、DBにセットする
        score_list = []
        for tweet in self.tweets.find(search_condition, {'id': 1, 'text': 1}):
            score = self._calc_negaposi_socore(tweet["text"])
            score_list.append(score)
            self.tweets.update({'_id': tweet['_id']}, {'$set': {'negaposi': score}})
            # print("text: {}".format(tweet["text"]))
            # print("score: {}".format(score))
        ave = np.array(score_list).mean()
        print("ネガポジスコアの平均値は、{}でした。".format(ave))
        self.log.info("ネガポジスコアの算出完了")

    def _calc_negaposi_socore(self, text: str) -> float:
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
                                  if (m.part_of_speech in ("形容詞", "動詞", "助詞")) and
                                  (m.polarity < -0.5 or m.polarity > 0.0)])
            """
            polarity_list.extend([m.polarity for m in m_list
                                  if (abs(m.polarity) > 0.8 and m.part_of_speech != "名詞") or (abs(m.polarity) > 0.5)])
            """

        # 極性の平均値を算出する。
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
            ft = node.feature.split(",")
            word = node.surface
            original_form = ft[6]
            part_of_speech = ft[0]

            polarity = self._calc_polarity(word=word, original=original_form, part=part_of_speech)
            morpheme = Morpheme(word=word, part=part_of_speech, original=original_form, polarity=polarity)

            # 記号などは算出対象（リスト）に含めないようにする。
            if morpheme.part_of_speech != "BOS/EOS" and morpheme.part_of_speech != "記号":
                morpheme_list.append(morpheme)

            node = node.next

        return morpheme_list

    def _calc_polarity(self, word, original, part):
        """
        :param word:
        :param original:
        :param part:
        :return: 極性値
        """
        # http://www.lr.pi.titech.ac.jp/~takamura/pndic_en.html
        # ネガティブワードとして定義されているが、除外したいものは0.0を設定しておく。
        if (self.PN_DICT is None) or (word in ("印刷", "プリント", "写真", "用紙", "コピー", "ネット")):
            return 0.0
        elif original != "*":
            return self.PN_DICT.get((original, part), float(0))
        else:
            return self.PN_DICT.get((word, part), float(0))

    @staticmethod
    def _init_pn_dict() -> dict:
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
