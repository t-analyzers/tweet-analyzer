import pandas as pd
from sklearn import svm
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.grid_search import GridSearchCV

from mecab_analyzer import MecabAnalyzer
from shared.datetime_extentions import *
from shared.decorators import trace


# coding=utf-8
# write code...


class SvmScorer(MecabAnalyzer):
    """
    サポートベクターマシン（SVM）を使ってネガポジ判定を行うクラス
    """

    def __init__(self):
        super().__init__()

    @trace()
    def update_negaposi(self, start_datetime: datetime, end_datetime: datetime):
        search_condition = {'retweeted_status': {'$eq': None}, 'spam': {'$eq': None},
                            'created_datetime': {'$gte': start_datetime, '$lte': end_datetime}}

        target_tweets = self.tweets.find(search_condition, {'id': 1, 'text': 1})

        # 改行コードを削除した文字列のSeriesを生成する。
        text_series = pd.Series([tweet['text'].replace('\n', '') for tweet in target_tweets])

        # SVM による分類
        print("[INFO] SVM (分類)")
        self.log.info("[INFO] SVM (分類)")
        score_series = self._svm_learn(target_series=text_series)

        for (tweet, score) in zip(target_tweets, score_series):
            # TODO
            # self.tweets.update({'_id': tweet['_id']}, {'$set': {'negaposi': score}})
            print(score)

    def _svm_learn(self, target_series):
        sample_tweets = self._init_sample_tweets()
        feature_vectors, vocabulary = self._extract_feature_vectors_and_vocabulary(sample_tweets['wakati'])

        # SVM による学習
        print("[INFO] SVM (グリッドサーチ)")
        svm_tuned_parameters = [
            {
                'kernel': ['rbf'],
                'gamma': [2 ** n for n in range(-15, 3)],
                'C': [2 ** n for n in range(-5, 15)]
            }
        ]

        grid_search_CV = GridSearchCV(
            svm.SVC(),
            svm_tuned_parameters,
            cv=5,  # クロスバリデーションの分割数
            n_jobs=1,  # 並列スレッド数
            verbose=3  # 途中結果の出力レベル0だと出力しない
        )
        grid_search_CV.fit(feature_vectors, list(sample_tweets['score']))
        svm_model = grid_search_CV.best_estimator_
        print(svm_model)

        # 学習時の vocabulary を指定する
        count_vectorizer = CountVectorizer(vocabulary=vocabulary)

        split_iterable_text = target_series.apply(self._wakati)
        target_feature_vectors = count_vectorizer.fit_transform(split_iterable_text)

        return svm_model.predict(target_feature_vectors)

    def _extract_feature_vectors_and_vocabulary(self, iterable_documents):
        """
        BoW (Term Frequency) 素性ベクトルへ変換
        :param iterable_documents:
        :return:
            feature_vectors: scipy.sparse の csr_matrix 形式
            vocabulary: 列要素(単語) 名
        """
        self.log.info("[INFO] 素性ベクトル作成")
        print("[INFO] 素性ベクトル作成")
        count_vectorizer = CountVectorizer()
        feature_vectors = count_vectorizer.fit_transform(iterable_documents)
        vocabulary = count_vectorizer.get_feature_names()
        return feature_vectors, vocabulary

    def _init_sample_tweets(self) -> pd.DataFrame:
        """
        tsv（教師データ）を読み込んでDataFrameを返す。
        :return: DataFrame
        """
        self.log.info("教師データの生成")
        sample_tweets = pd.read_csv('conf/sample_tweets.tsv', delimiter='\t', header=None, names=('text', 'score'))
        sample_tweets['wakati'] = sample_tweets['text'].apply(self._wakati)
        return sample_tweets

    def _wakati(self, sentence: str) -> str:
        """
        形態素に分割し、名詞・動詞(終止形)・形容詞のみを抽出
        :param sentence:
        :return: 形態素解析で抽出した単語を半角スペースで連結した文字列
        """
        print("[INFO] 分かち書き")
        self.tagger.parse("")
        node = self.tagger.parseToNode(sentence)
        word_list = []

        while node:
            ft = node.feature.split(",")
            if ft[0] in ["名詞", "動詞", "形容詞"]:
                lemma = ft[6]
                if lemma == "*":
                    lemma = node.surface
                word_list.append(lemma)
            node = node.next
        # TODO
        # ここのスライスの意図が分からない。なぜ最初と最後の単語を省くのか。
        return " ".join(word_list[1:-1])


if __name__ == '__main__':
    today = datetime.today()
    tomorrow = today + timedelta(days=1)
    # Twitter APIでは最大7-10日間分くらい検索可能なので、それよりも広めな14日間の範囲で検索する。
    two_weeks_ago = tomorrow - timedelta(days=14)
    SvmScorer().set_negaposi_score(two_weeks_ago, tomorrow)
