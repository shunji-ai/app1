from flask import Flask, request, render_template_string
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# --- Flaskアプリの初期化 ---
app = Flask(__name__)

# --- HTMLテンプレート ---
# Webページの見た目を定義します。CSSフレームワークTailwindを使用しています。
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>株価チェッカー・ウェブアプリ</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', 'Noto Sans JP', sans-serif; }
        table { border-collapse: collapse; }
        th, td { text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body class="bg-gray-100 text-gray-800">
    <div class="container mx-auto p-4 md:p-8 max-w-5xl">
        <header class="text-center mb-8">
            <h1 class="text-3xl md:text-4xl font-bold text-gray-900">株価チェッカー</h1>
            <p class="mt-2 text-gray-600">Yahooファイナンスのデータを使い、複数銘柄の過去の株価を取得します。</p>
        </header>

        <main class="bg-white p-6 rounded-2xl shadow-lg">
            <form method="post">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div class="md:col-span-2 flex flex-col">
                        <label for="tickers" class="mb-2 font-semibold text-gray-700">銘柄コード</label>
                        <textarea id="tickers" name="tickers" rows="4" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" placeholder="例: 7203.T, 9984.T, AAPL&#10;カンマ(,)、スペース、改行で区切って入力" required>{{ tickers_value }}</textarea>
                    </div>
                    <div class="flex flex-col">
                        <label for="start_date" class="mb-2 font-semibold text-gray-700">開始日</label>
                        <input type="date" id="start_date" name="start_date" value="{{ start_date_value }}" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required>
                    </div>
                     <div class="flex flex-col">
                        <label for="end_date" class="mb-2 font-semibold text-gray-700">終了日</label>
                        <input type="date" id="end_date" name="end_date" value="{{ end_date_value }}" class="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500" required>
                    </div>
                </div>
                <div class="mt-6 text-center">
                    <button type="submit" class="w-full md:w-auto bg-blue-600 text-white font-bold py-3 px-8 rounded-lg hover:bg-blue-700 transition-all">株価を取得</button>
                </div>
            </form>
        </main>

        {% if error_message %}
        <div class="mt-8 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-lg" role="alert">
            <p class="font-bold">エラー</p>
            <p>{{ error_message }}</p>
        </div>
        {% endif %}

        {% if results_html %}
        <div class="mt-8 bg-white p-6 rounded-2xl shadow-lg">
            <h2 class="text-2xl font-bold mb-4 text-center">取得結果 (終値)</h2>
            <div class="overflow-x-auto">
                {{ results_html | safe }}
            </div>
        </div>
        {% endif %}

    </div>
</body>
</html>
"""

# --- 株価取得ロジック ---
def get_stock_data_for_web(tickers, start_date, end_date):
    """yfinanceを使い、1銘柄ずつ順番に株価データを取得し、終値を1つの表にまとめる"""
    try:
        # 終了日に1日を加算して、指定日当日も範囲に含める
        end_date_inclusive = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError("日付の形式が正しくありません。")

    combined_data = pd.DataFrame()

    for ticker in tickers:
        if not ticker: continue
        print(f"銘柄: {ticker} のデータを取得中...")
        try:
            data = yf.download(ticker, start=start_date, end=end_date_inclusive, progress=False, auto_adjust=True)
            
            if data.empty:
                print(f"  -> {ticker} のデータが見つかりませんでした。")
                continue
            
            # yfinanceのauto_adjust=Trueは'Close'列に調整後終値を返す
            combined_data[ticker] = data['Close']
            print(f"  -> 取得成功")
        except Exception as e:
            print(f"  -> {ticker} の取得中にエラーが発生しました: {e}")
            # エラーが発生した銘柄はスキップして次の銘柄へ
            continue
            
    return combined_data

# --- Webサーバーのルーティング ---
@app.route('/', methods=['GET', 'POST'])
def index():
    """メインページを処理する"""
    results_html = None
    error_message = None
    # フォームの初期値を設定
    tickers_value = "7203.T, 9984.T, AAPL, MSFT"
    end_date_value = datetime.today().strftime("%Y-%m-%d")
    start_date_value = (datetime.today() - timedelta(days=14)).strftime("%Y-%m-%d")

    if request.method == 'POST':
        # フォームから送信されたデータを取得
        tickers_value = request.form.get('tickers')
        start_date_value = request.form.get('start_date')
        end_date_value = request.form.get('end_date')
        
        if not all([tickers_value, start_date_value, end_date_value]):
            error_message = "すべての項目を入力してください。"
        else:
            # カンマ、スペース、改行で区切られた銘柄コードをリストに変換
            tickers_list = [t.strip() for t in tickers_value.replace(',', ' ').split()]
            
            try:
                # 株価取得関数を呼び出し
                results_df = get_stock_data_for_web(tickers_list, start_date_value, end_date_value)
                
                if not results_df.empty:
                    # pandas DataFrameをHTMLテーブルに変換
                    results_html = results_df.to_html(
                        classes="min-w-full divide-y divide-gray-200", 
                        float_format='{:.2f}'.format
                    )
                else:
                    error_message = "指定された期間・銘柄のデータが見つかりませんでした。"
            except Exception as e:
                error_message = f"処理中にエラーが発生しました: {e}"
    
    # HTMLテンプレートに変数を渡してページを生成
    return render_template_string(
        HTML_TEMPLATE,
        results_html=results_html,
        error_message=error_message,
        tickers_value=tickers_value,
        start_date_value=start_date_value,
        end_date_value=end_date_value
    )

# --- アプリケーションの実行 ---
if __name__ == '__main__':
    # スクリプトが直接実行された場合にWebサーバーを起動
    print("Webサーバーを起動します...")
    print("ブラウザで http://127.0.0.1:5000 にアクセスしてください。")
    print("サーバーを停止するには、ターミナルで Ctrl + C を押してください。")
    # 修正点: host='0.0.0.0' を '127.0.0.1' に変更
    app.run(host='127.0.0.1', port=5000, debug=False)
