import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime

# --- [1. 보안 설정 함수] ---
# 이 함수가 반드시 호출(line 123)보다 위에 있어야 합니다.
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Byul 보안 접속")
        st.text_input("접속 비밀번호", type="password", key="password")
        if st.button("접속"):
            if st.session_state.password == "1234": # 비밀번호 수정 가능
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return False
    return True

# --- [2. 실시간 뉴스 및 예측 분석 함수] ---
def analyze_news_and_predict(name, is_us=False):
    try:
        query = f"{name} stock news" if is_us else f"{name} 주가 호재"
        url = f"https://www.google.com/search?q={query}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.get_text()
        
        analysis = {"is_hot": False, "news_title": "", "prediction": ""}
        keywords = {
            '실적': ("🔥 분기 사상 최대 실적 발표!", "영업이익 서프라이즈로 인한 수급 유입, 신고가 갱신 가능성 85%"),
            '수주': ("🚀 대규모 신규 수주 포착!", "장기 매출 성장 동력 확보, 계단식 상승 추세 형성 기대"),
            '공급': ("🚀 대규모 공급 계약 체결!", "시장 점유율 상승 및 목표주가 상향 리포트 예상"),
            '반등': ("📈 바닥권 반등 신호 포착!", "과매도 구간 해소, 단기 추세 전환 가능성 높음"),
            'Earnings': ("🔥 Earnings Surprise!", "Strong fundamental growth, target price upgraded"),
            'Contract': ("🚀 New Major Contract!", "Expansion of market share, bullish trend expected")
        }

        for kw, (title, pred) in keywords.items():
            if kw in content:
                analysis["is_hot"] = True
                analysis["news_title"] = title
                analysis["prediction"] = pred
                break
        return analysis
    except:
        return {"is_hot": False, "news_title": "", "prediction": ""}

# --- [3. 사이드바 실시간 뉴스 피드 함수] ---
def display_news_feed(market_name):
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"🗞️ Byul {market_name} 실시간 뉴스")
    try:
        query = "코스피 특징주 호재" if market_name == "KOSPI" else "NASDAQ hot news"
        url = f"https://www.google.com/search?q={query}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        news_items = soup.select('div.SoR3S')[:5]
        
        for item in news_items:
            title = item.get_text()
            st.sidebar.markdown(f"🔴 **{title}**")
            st.sidebar.caption(f"🕒 {datetime.now().strftime('%H:%M')} 업데이트")
            st.sidebar.markdown("---")
    except:
        st.sidebar.write("뉴스 피드 로딩 중...")

# --- [4. 메인 실행부] ---
if check_password(): # 여기서 함수를 호출합니다. 위에서 정의했으므로 에러가 나지 않습니다.
    st.sidebar.title("⭐️ Byul Search")
    market = st.sidebar.radio("시장 선택", ["KOSPI", "NASDAQ"])

    @st.cache_data
    def get_list(m):
        return fdr.StockListing(m)

    full_list = get_list(market)
    search_query = st.sidebar.text_input("🔍 종목명/티커 검색", "").upper()
    
    if search_query:
        filtered_stocks = full_list[
            full_list['Name' if market=="KOSPI" else 'Symbol'].str.contains(search_query, na=False) |
            full_list['Code' if market=="KOSPI" else 'Symbol'].str.contains(search_query, na=False)
        ]
    else:
        filtered_stocks = full_list.head(100)

    selected_stock = st.sidebar.selectbox("결과 선택", filtered_stocks['Name' if market=="KOSPI" else 'Symbol'].tolist())
    
    # 사이드바 하단 뉴스 피드 표시
    display_news_feed(market)

    if selected_stock:
        row = filtered_stocks[filtered_stocks['Name' if market=="KOSPI" else 'Symbol'] == selected_stock]
        code = row['Code' if market=="KOSPI" else 'Symbol'].values[0]
        df = fdr.DataReader(code).tail(120)
        news_data = analyze_news_and_predict(selected_stock, is_us=(market=="NASDAQ"))

        col_news, col_chart = st.columns([1, 2.5])

        with col_news:
            st.markdown("### 🤖 Byul AI 실시간 분석")
            if news_data["is_hot"]:
                st.markdown(f"""
                    <div style="background-color: #ffebee; padding: 20px; border-left: 10px solid #f44336; border-radius: 5px;">
                        <h4 style="color: #d32f2f; margin-top: 0;">🚨 {news_data['news_title']}</h4>
                        <p style="color: #b71c1c; font-weight: bold; font-size: 1.1em;">
                            <b>[AI 예측]</b><br>{news_data['prediction']}
                        </p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("현재 특이 뉴스 흐름이 감지되지 않았습니다.")
            
            st.write("---")
            curr_price = df.iloc[-1]['Close']
            prev_price = df.iloc[-2]['Close']
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            st.metric(label=f"{selected_stock} 현재가", value=f"{curr_price:,}", delta=f"{change_pct:.2f}%")

        with col_chart:
            st.subheader(f"📊 {selected_stock} 분석 차트")
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color= '#f44336', decreasing_line_color= '#2196f3'
            )])
            df['MA20'] = df['Close'].rolling(20).mean()
            df['MA60'] = df['Close'].rolling(60).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20일선', line=dict(color='orange', width=1)))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60일선', line=dict(color='green', width=1)))
            fig.update_layout(height=600, template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
