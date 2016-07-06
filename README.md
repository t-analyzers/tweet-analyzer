# tweet-analyzer
This is a test repository for twitter analysis.

### 事前準備

#### Python3
Python3.5をインストールする。  
pandasを使っているのと機械学習系のライブラリを使ってみたい場合は、  
Anacondaをインストールすると主要なライブラリをまとめてインストールできるのでおすすめ。  
https://www.continuum.io/downloads

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
analyzer/config.pyの下記項目に各自の値を設定する。    
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

#### simple_analyzer.py
簡単な集計を行い、DataFrameを生成します。

#### report_creator.py
DBから過去1周間以内のつぶやきを検索し、dataフォルダ以下にExcel出力します。  
時間ごと、日ごと、時間帯別のつぶやき数を集計します。  
などなど。  

### Jupyter Notebook
Anacondaを使っていればインストール済です。  
下記コマンドを実行すると起動します。  
起動後、twitter_analysis.ipynbを開いてください。  
```
jupyter notebook
```