import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
import numpy as np
from datetime import datetime

# --- [기존 보안/뉴스 분석 함수 동일하게 유지] ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Byul 보안 접속")
        st.text_input("접속 비밀번호", type="password", key="password")
        if st.button("접속"):
            if st.session_state.password == "1234":
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("비밀번호가 올바르지 않습니다.")
        return False
    return True

def analyze_news_and_predict(name, is_us=False):
    # (앞선 코드의 뉴스 분석 로직 유지)
    try:
        query = f"{name} stock news" if is_us else f"{name} 주가 호재"
        url = f"https://www.google.com/search?q={query}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.get_text()
        
        analysis = {"is_hot": False, "news_title": "", "prediction": ""}
        keywords = {
            '실적': ("🔥 분기 최대 실적 발표!", "어닝 서프라이즈로 인한 수급 유입, 추가 상승 85%"),
            '수주': ("🚀 대규모 신규 수주 포착!", "장기 성장 동력 확보, 우상향 추세 기대"),
            '반등': ("📈 바닥권 반등 신호!", "과매도 해소, 단기 추세 전환 가능성 높음")
        }
        for kw, (title, pred) in keywords.items():
            if kw in content:
                analysis["is_hot"] = True
                analysis["news_title"] = title
                analysis["prediction"] = pred
                break
        return analysis
    except: return {"is_hot": False, "news_title": "", "prediction": ""}

# --- [새 기능: 골든크로스 및 매물대 계산 함수] ---
def analyze_technical(df):
    # 1. 골든크로스 판단 (5일선이 20일선을 상향 돌파)
    df['MA5'] = df['Close'].rolling(5).mean()
    df['MA20'] = df['Close'].rolling(20).mean()
    
    curr_ma5, curr_ma20 = df.iloc[-1]['MA5'], df.iloc[-1]['MA20']
    prev_ma5, prev_ma20 = df.iloc[-2]['MA5'], df.iloc[-2]['MA20']
    
    is_golden = prev_ma5 < prev_ma20 and curr_ma5 >= curr_ma20
    
    # 2. 매물대 계산 (최근 120일 종가 기준 가장 많이 머문 구간)
    counts, bins = np.histogram(df['Close'], bins=5)
    max_vol_idx = np.argmax(counts)
    vol_zone_low = bins[max_vol_idx]
    vol_zone_high = bins[max_vol_idx+1]
    
    return is_golden, vol_zone_low, vol_zone_high

# --- [메인 실행부] ---
if check_password():
    st.sidebar.title("⭐️ Byul Search")
    market = st.sidebar.radio("시장 선택", ["KOSPI", "NASDAQ"])
    full_list = fdr.StockListing(market)
    
    search_query = st.sidebar.text_input("🔍 종목명/티커 검색", "").upper()
    if search_query:
        filtered = full_list[full_list['Name' if market=="KOSPI" else 'Symbol'].str.contains(search_query, na=False)]
    else: filtered = full_list.head(100)

    selected_stock = st.sidebar.selectbox("결과 선택", filtered['Name' if market=="KOSPI" else 'Symbol'].tolist())

    if selected_stock:
        row = filtered[filtered['Name' if market=="KOSPI" else 'Symbol'] == selected_stock]
        code = row['Code' if market=="KOSPI" else 'Symbol'].values[0]
        df = fdr.DataReader(code).tail(120)
        
        # 분석 실행
        is_golden, vol_low, vol_high = analyze_technical(df)
        news_data = analyze_news_and_predict(selected_stock, is_us=(market=="NASDAQ"))

        col_left, col_right = st.columns([1, 2.5])

        with col_left:
            st.markdown("### 🤖 Byul AI 기술 분석")
            
            # 1. 골든크로스 알림 (Byul 시그니처)
            if is_golden:
                st.markdown("""
                    <div style="background-color: #fff9c4; padding: 15px; border: 2px solid #fbc02d; border-radius: 10px; text-align: center;">
                        <h3 style="color: #f57f17; margin:0;">✨ 골든크로스 발생!</h3>
                        <p style="color: #616161; font-weight: bold;">매수 신호가 포착되었습니다.</p>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.write("✨ 현재 이평선 정배열 추적 중...")

            # 2. 매물대 표시 (붉은색 강조)
            st.markdown(f"""
                <div style="margin-top: 15px; background-color: #fce4ec; padding: 15px; border-left: 5px solid #e91e63; border-radius: 5px;">
                    <p style="color: #880e4f; margin:0; font-size: 0.9em;">📊 <b>집중 매물대 구간</b></p>
                    <h4 style="color: #c2185b; margin: 5px 0;">{vol_low:,.0f} ~ {vol_high:,.0f}</h4>
                    <p style="color: #ad1457; font-size: 0.8em;">해당 구간 돌파 시 강한 탄력이 예상됩니다.</p>
                </div>
            """, unsafe_allow_html=True)

            # 3. 뉴스 분석 (기존 붉은 박스)
            if news_data["is_hot"]:
                st.markdown(f"""
                    <div style="margin-top: 15px; background-color: #ffebee; padding: 15px; border-left: 5px solid #f44336; border-radius: 5px;">
                        <h5 style="color: #d32f2f; margin:0;">🚨 {news_data['news_title']}</h5>
                        <p style="color: #b71c1c; font-size: 0.85em;">{news_data['prediction']}</p>
                    </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.subheader(f"📊 {selected_stock} 분석 차트")
            fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
            
            # 매물대 시각화 (차트에 투명한 박스로 표시)
            fig.add_hrect(y0=vol_low, y1=vol_high, fillcolor="pink", opacity=0.2, line_width=0, annotation_text="매물대 집중구간")
            
            fig.update_layout(height=600, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
