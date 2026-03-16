import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- [설정 부분] ---
TELEGRAM_TOKEN = '8714582588:AAEq4h3_CfAPaLKkVmqxv8AqRJ3ym2XgGeI'
CHAT_ID = '8613977068'
# ------------------

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def get_us_analysis(keyword):
    reports = {
        'Bullish': ("강세 전환 신호 포착", "저항대 돌파로 상방 압력 증대", "신고가 경신 가능성"),
        'Surge': ("거래량 폭증 및 가격 급등", "강력한 매수 모멘텀 유입", "변동성 동반 추가 상승"),
        'Earnings': ("어닝 서프라이즈 발표", "실적 기반 가치 재평가", "중장기 우상향 채널 형성")
    }
    res = reports.get(keyword, ("기술적 수급 개선", "기관 투자자 유입 확인", "안정적 흐름 예상"))
    return f"📍 요점: {res[0]} / 🧐 분석: {res[1]} / 🔭 전망: {res[2]}"

def check_us_news_hot(symbol):
    try:
        url = f"https://www.google.com/search?q={symbol}+stock+news+bullish&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        kw_map = {'Bullish': '상승', 'Surge': '급등', 'Earnings': '실적'}
        news_content = soup.get_text()
        for eng, kor in kw_map.items():
            if eng in news_content: return eng
        return ""
    except: return ""

def run_nasdaq_ai_report():
    df_nasdaq = fdr.StockListing('NASDAQ').head(1000)
    candidate_list = []
    for index, row in df_nasdaq.iterrows():
        symbol, name = row['Symbol'], row['Name']
        try:
            df = fdr.DataReader(symbol).tail(60)
            if len(df) < 30: continue
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            curr, prev = df.iloc[-1], df.iloc[-2]
            
            support = round(df['Low'].tail(20).min(), 2)
            gap = (curr['MA20'] - curr['MA5']) / curr['MA20']
            is_gold = 0 < gap < 0.025 and (curr['MA5'] > prev['MA5'])
            change = round(((curr['Close'] - prev['Close']) / prev['Close']) * 100, 2)
            
            news_kw = ""
            if is_gold or change > 5:
                news_kw = check_us_news_hot(symbol)
            
            if is_gold or news_kw:
                score = change + (15 if is_gold else 0) + (10 if news_kw else 0)
                candidate_list.append({
                    '티커': symbol, '기업명': name, '현재가($)': round(curr['Close'], 2),
                    '하단선($)': support, '등락률(%)': change, '호재뉴스': news_kw if news_kw else '기술적강세',
                    'AI분석': get_us_analysis(news_kw), 'Score': score
                })
        except: continue

    final_df = pd.DataFrame(candidate_list).sort_values(by='Score', ascending=False).head(40)
    if not final_df.empty:
        final_df.drop('Score', axis=1).to_excel("나스닥_핵심_TOP40.xlsx", index=False)
        send_msg("🇺🇸 나스닥 분석 완료 및 대시보드 업데이트")

if __name__ == "__main__":
    run_nasdaq_ai_report()
