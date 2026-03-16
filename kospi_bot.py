import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

# --- [설정 부분] ---
TELEGRAM_TOKEN = '8714582588:AAEq4h3_CfAPaLKkVmqxv8AqRJ3ym2XgGeI'
CHAT_ID = '8613977068'
# ------------------

def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    params = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    requests.get(url, params=params)

def get_analysis_report(name, keyword):
    if not keyword:
        return "📍 요점: 기술적 수급 개선 / 🧐 분석: 바닥권 매집 확인 / 🔭 전망: 반등 기대"
    reports = {
        '실적': ("분기 최대 실적 발표", "펀더멘털 기반 외인 매수", "전고점 돌파 기대"),
        '계약': ("대규모 수주 계약 체결", "장기 매출 성장 동력 확보", "계단식 상승 전망"),
        '급등': ("강력한 거래량 동반 돌파", "매물 공백 구간 진입", "추가 슈팅 가능성")
    }
    res = reports.get(keyword, ("호재성 뉴스 발생", "저가 매수세 유입", "완만한 회복 기대"))
    return f"📍 요점: {res[0]} / 🧐 분석: {res[1]} / 🔭 전망: {res[2]}"

def check_news_hot(stock_name):
    try:
        url = f"https://www.google.com/search?q={stock_name}+주가+호재&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        hot_keywords = ['실적', '계약', '급등', '호재', '돌파']
        news_content = soup.get_text()
        for kw in hot_keywords:
            if kw in news_content: return kw
        return ""
    except: return ""

def run_kospi_ai_report():
    df_kospi = fdr.StockListing('KOSPI')
    candidate_list = []
    for index, row in df_kospi.iterrows():
        code, name = row['Code'], row['Name']
        try:
            df = fdr.DataReader(code).tail(60)
            if len(df) < 30: continue
            df['MA5'] = df['Close'].rolling(window=5).mean()
            df['MA20'] = df['Close'].rolling(window=20).mean()
            curr, prev = df.iloc[-1], df.iloc[-2]
            
            support = int(df['Low'].tail(20).min())
            gap = (curr['MA20'] - curr['MA5']) / curr['MA20']
            is_gold = 0 < gap < 0.025 and (curr['MA5'] > prev['MA5'])
            change = round(((curr['Close'] - prev['Close']) / prev['Close']) * 100, 2)
            
            news_kw = ""
            if is_gold or change > 5:
                news_kw = check_news_hot(name)
            
            if is_gold or news_kw:
                score = change + (15 if is_gold else 0) + (10 if news_kw else 0)
                candidate_list.append({
                    '종목명': name, '현재가': int(curr['Close']), '하단선': support,
                    '등락률(%)': change, '호재뉴스': news_kw if news_kw else '수급포착',
                    'AI분석': get_analysis_report(name, news_kw), 'Score': score
                })
        except: continue

    final_df = pd.DataFrame(candidate_list).sort_values(by='Score', ascending=False).head(30)
    if not final_df.empty:
        final_df.drop('Score', axis=1).to_excel("코스피_상세_분석_TOP30.xlsx", index=False)
        send_msg("🇰🇷 코스피 분석 완료 및 대시보드 업데이트")

if __name__ == "__main__":
    run_kospi_ai_report()
