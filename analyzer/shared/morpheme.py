import MeCab

# coding=utf-8
# write code...


class Morpheme(object):
    """
    形態素の情報を格納するクラス
    """

    def __init__(self, node: MeCab.Node, pn_dict: dict = None):
        """
        :param node: 文頭->http://taku910.github.io/mecab/bindings.html
        :param pn_dict: 日本語評価極性辞書を変換した辞書オブジェクト
        """
        ft = node.feature.split(",")
        original_form = ft[6]

        self.word = node.surface
        self.part_of_speech = ft[0]

        # http://www.lr.pi.titech.ac.jp/~takamura/pndic_en.html
        # ネガティブワードとして定義されているが、除外したいものは0.0を設定しておく。
        if (pn_dict is None) or (self.word in ("印刷", "プリント", "写真", "用紙", "コピー", "ネット")):
            self.polarity = 0.0
        elif original_form != "*":
            self.polarity = pn_dict.get((original_form, self.part_of_speech), float(0))
        else:
            self.polarity = pn_dict.get((self.word, self.part_of_speech), float(0))
