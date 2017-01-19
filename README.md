# tweet-analyzer
This is a test repository for twitter analysis.

### 事前準備

#### Python3
Python3.5をインストールする。  
pandasを使っているのと機械学習系のライブラリを使ってみたい場合は、  
[Anaconda](https://www.continuum.io/downloads)をインストールすると主要なライブラリをまとめてインストールできるのでおすすめ。  

その他必要なライブラリは、requirements.txtに記載。  
Pythonをインストール後、下記コマンドを実行すればまとめてインストールできます。  
```
pip install -r requirements.txt
```

#### 作業用ディレクトリについて
analyzer以下にソースコードがあります。   
out以下にExcelを出力します。  
logs以下にログ出力します。  

#### Twitter API
TwitterAPIが必要なので、取得する。  
analyzer/conf/config.pyの下記項目に各自の値を設定する。    
* CONSUMER_KEY
* CONSUMER_SECRET
* ACCESS_TOKEN_KEY
* ACCESS_TOKEN_SECRET

プロキシ環境下では下記項目に設定が必要。
* PROXY

#### MongoDB
Twitter APIで取得したつぶやき（JSON）をMongoDBに格納します。  
MongoDBをインストールして起動しておく。  
ホスト名やポート番号は、config.pyで設定しているので必要に応じて変更する。  

- インデックスの追加  
mongoコマンドでコンソールを開き、インデックスを追加してください。    
created_datetimeキーに対して、基本的な降順インデックスを追加するコマンドは下記です。   
インデックスについての詳細は、[公式ページ](https://docs.mongodb.com/manual/reference/method/db.collection.createIndex/#db.collection.createIndex)を参照してください。  

```
use twitter-archive
db.tweets.createIndex({created_datetime: -1})
```

#### Mecabのユーザ辞書
※本項目はオプションです。実施しなくてもスクリプトは動作します。  
一部のスクリプトで形態素解析を行っていますが、  
精度を向上させるためにユーザ辞書を追加でインストールしてください。  
インストール方法は、[mecab-ipadic-neologd](https://github.com/neologd/mecab-ipadic-neologd/blob/master/README.ja.md)を参照してください。  
インストール後、analyzer/conf/config.pyの下記項目にインストールパスを設定してください。  
* MECAB_USER_DICT

### 実行方法
command.pyが実行用のスクリプトになっています。  
引数にコマンド名を指定すると処理が開始されます。  

Twitter APIを使用してつぶやきを保存する場合：  
```
cd analyzer  
python command.py a  
```

Excel形式のレポートを出力する場合：  
```
cd analyzer  
python command.py e  
```

### 各スクリプトについて

#### archiver.py
search_keywords.ymlに記載されたキーワードのリストをOR連結し、検索キーワードとして使用します。  
新しいつぶやきから順に検索結果が得られなくなるまで検索を繰り返します。  
おそらく過去1週間程度まで取得可能です。（詳細は、TwitterAPIを参照）  
また、検索開始時、DBに格納されている中で最新のつぶやきのidを取得しており、検索の終了条件に使用しています。  
そのため検索範囲は、「最新のつぶやき〜DBに格納されている最新のつぶやき」となります。  
検索完了後、created_datetimeキーにUTCから日本時間に変換した値をセットしています。  

#### spam_detector.py
1時間以内に60回以上リツイートされているものはスパム判定しています。  
該当する場合、DBに対して更新（{'spam': True}をセット）をかけます。

#### sample_analyzer.py
簡単な集計を行い、DataFrameを生成します。

#### tweet_counter.py
時間帯別のつぶやき数を集計し、DataFrameを生成します。

#### report_creator.py
DBから過去1周間以内のつぶやきを検索し、dataフォルダ以下にExcel出力します。  
時間ごと、日ごと、時間帯別のつぶやき数を集計します。  
などなど。  

#### pn_dict_scorer.py
現状は、単語感情極性対応を用いて文章（つぶやき）の極性値をネガポジスコアとして算出します。  

#### svm_scorer.py
サポートベクターマシンを使ってネガポジ判定を行います。
conf/sample_tweets.tsvを教師データとしています。

#### svm_scorer_using_metadata.py
サポートベクターマシンを使ってネガポジ判定を行います。
create_learning_data_using_metadata.pyで作成した教師データを使用します。
接続先のMongoDBの情報などはconfig_svm_np.pyで設定します。
なお、ロジックは[【特別連載】 さぁ、自然言語処理を始めよう！（最終回： 機械学習によるテキストマイニング）](https://datumstudio.jp/backstage/662 "機械学習によるテキストマイニング")を参考に作成しました。

教師データのコレクションをエクスポートしたファイルは以下に格納しています：
/out/tweets-metadata.jbos
このフォルダ(out)へ移動し、以下のコマンドで上書きリストアできます。
```
mongorestore -drop -d twitter-archive -c tweets-metadata  ./tweets-metadata.bson
```

#### create_learning_data_using_metadata.py
metadata株式会社の「高精度ネガポジAPI」を使用してツイート本文のネガポジを判定し、教師データを作成します。
ツイート本文の取得先及び教師データの格納先はMongoDBです。
APIキーやMongoDBの情報はconfig_metadata_api.pyで設定します。

#### feature_words_extractor.py
archive.pyで取り込んだツイートをMeCabを使って形態素解析を行い名詞を抽出し、TF-IDFモデルで日別の特徴語を抽出します。
抽出結果はJSON形式と画像で以下のようにファイルに出力します。

* 特徴語データ:
feature_words_YYYYMMDD-YYYYMMDD.json:[{"date": 日付, "tweet_count":ツイート数, "retweet_count":リツイート数,
"posi_count":ポジティブツイート数, "nega_count":ネガティブツイート数,"feature_words":[特徴語リスト]},...] ※dateでソート
* 特徴語データファイルリスト:
filelist-feature_words.json: 特徴語データ出力先フォルダ内の特徴語データファイルのリスト（降順）。"feature_words_"で始まるファイルが対象。
* 日別ツイートデータ:
tweets_YYYYMMDD.json:  [{'created_datetime': 日時,'retweet_count':収集時点のリツイート数, 'id': ツイートのID, user.screen_name': ツイッターアカウント名, 'text':ツイート本文, 'media_urls':画像URL, 'nouns':ツイート本文内の名詞（半角スペースで連結) ,'PrintID':プリント予約番号 }, ...] ※created_datetimeでソート
* ツイートファイルリスト:
filelist-tweets.json: 日別ツイートデータ出力先フォルダ内の日別ツイートデータファイルのリスト（降順）。"tweets_"ではじまるファイルが対象。
* 日別ワードクラウド画像:
wordcloud_YYYYMMDD.png

解析する日数、抽出する特徴語の数、ファイル出力先フォルダはconfig_feature_words.pyで指定できます。
また、本プログラムでは以下のライブラリを使用します。（Anacondaをインストールするとこれらのライブラリはインストール済みのようです。）

* mecab-python3: MeCab自身のインストール方法は　[Python で Mecabを利用する【mac】](http://inner2.hatenablog.com/entry/2015/01/08/230447 "Python で Mecabを利用する【mac】")を参照のこと。(macですが)
* scikit-learn
* scipy
* numpy

なお、ロジックは[【特別連載】 さぁ、自然言語処理を始めよう！（第2回： 単純集計によるテキストマイニング）](https://datumstudio.jp/backstage/643 "単純集計によるテキストマイニング")を参考に作成しました。

#### image_analyzer.py
画像を分析する機能を実装。引数を指定して機能を実行する。
* hash：　実行日前日1日分のツイートから画像を取得し、予め特定フォルダに格納しておいた画像と類似している画像のツイートに {"hash_match": "(一致した画像ファイル名（拡張子なし）)"}を付加する。



### ユニットテスト
ユニットテストの実装には標準モジュールの[unittest](http://docs.python.jp/3/library/unittest.html)を使用しています。  
テストランナーには、[pytest](http://pytest.org/latest-ja/)が便利なのでインストールしてください。  
もちろんpytestでユニットテストを実装しても構いません。  
ルートディレクトリで下記コマンドを実行すると、テストを実行できます。  
詳細なオプションについては公式サイトを参照してください。  
```
py.test
```

### Jupyter Notebook
Anacondaを使っていればインストール済です。  
下記コマンドを実行すると起動します。  
起動後、twitter_analysis.ipynbを開いてください。  
```
jupyter notebook
```
