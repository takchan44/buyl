import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# --- [1. 보안 및 분석 로직] ---
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Byul 보안 접속")
        pwd = st.text_input("접속 비밀번호", type="password")
        if st.button("접속"):
            if pwd == "1234":
                st.session_state.password_correct = True
                st.rerun()
            else: st.error("비밀번호 불일치")
        return False
    return True

def get_realtime_news_analysis(name, is_us=False):
    try:
        query = f"{name} stock news" if is_us else f"{name} 주가 호재"
        url = f"https://www.google.com/search?q={query}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 뉴스 제목 추출 (강화된 파싱)
        news_links = soup.find_all('div', {'role': 'heading'}) or soup.find_all('h3')
        content = soup.get_text()
        
        analysis = {"is_hot": False, "news_title": "특이사항 없음", "prediction": "", "feed": []}
        
        for item in news_links[:5]:
            analysis["feed"].append(item.get_text())

        keywords = {'실적': "실적 서프라이즈", '수주': "신규 계약 체결", '반등': "기술적 반등"}
        for kw, title in keywords.items():
            if kw in content:
                analysis["is_hot"] = True
                analysis["news_title"] = f"🚨 {title} 포착!"
                analysis["prediction"] = f"현재 {kw} 모멘텀으로 인한 수급 유입 중. 목표가 상향 가능성 높음."
                break
        return analysis
    except: return {"is_hot": False, "news_title": "", "prediction": "", "feed": []}

# --- [2. 메인 실행부] ---
if check_password():
    st.sidebar.title("⭐️ Byul Search")
    market = st.sidebar.radio("시장 선택", ["KOSPI", "NASDAQ"])
    
    # 그래프 크기 조절 슬라이더 (사용자 요청)
    chart_height = st.sidebar.slider("📊 그래프 높이 조절", 400, 1000, 700)
    
    @st.cache_data
    def get_full_list(m): return fdr.StockListing(m)
    
    full_list = get_full_list(market)
    search = st.sidebar.text_input("🔍 종목명/티커 검색").upper()
    
    if search:
        filtered = full_list[full_list['Name' if market=="KOSPI" else 'Symbol'].str.contains(search, na=False)]
    else: filtered = full_list.head(100)
    
    selected = st.sidebar.selectbox("종목 선택", filtered['Name' if market=="KOSPI" else 'Symbol'].tolist())

    if selected:
        row = filtered[filtered['Name' if market=="KOSPI" else 'Symbol'] == selected]
        code = row['Code' if market=="KOSPI" else 'Symbol'].values[0]
        df = fdr.DataReader(code).tail(120)
        
        # --- 기술 지표 계산 ---
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        # 골든크로스 지점 찾기
        df['GC'] = (df['MA5'] >= df['MA20']) & (df['MA5'].shift(1) < df['MA20'].shift(1))
        
        # 실시간 뉴스 가져오기
        news_data = get_realtime_news_analysis(selected, is_us=(market=="NASDAQ"))

        col_left, col_right = st.columns([1, 3])

        with col_left:
            # 1. 뉴스 분석 문구 (붉은색)
            if news_data["is_hot"]:
                st.markdown(f"""
                    <div style="background-color: #ffebee; padding: 15px; border-left: 5px solid #f44336; margin-bottom:10px;">
                        <h4 style="color: #d32f2f; margin:0;">{news_data['news_title']}</h4>
                        <p style="color: #b71c1c; font-size: 0.9em;"><b>[AI 예측]</b><br>{news_data['prediction']}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            # 2. 실시간 뉴스 피드 (사이드바가 아닌 본문 왼쪽 하단)
            st.subheader("🗞️ 실시간 뉴스 피드")
            for n in news_data["feed"]:
                st.markdown(f"🔴 **{n}**")
                st.caption(f"🕒 {datetime.now().strftime('%H:%M')} 확인")
                st.write("---")

        with col_right:
            # --- 메인 차트 구성 (매물대 바 포함) ---
            # 캔들스틱과 매물대(가로 바)를 함께 그리기 위해 서브플롯 활용
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # 1. 캔들스틱
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="주가", increasing_line_color='#f44336', decreasing_line_color='#2196f3'
            ))

            # 2. 이동평균선
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name="5일선", line=dict(color='orange', width=1)))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="20일선", line=dict(color='green', width=1)))

            # 3. 골든크로스 화살표 표시 (그래프 안)
            gc_dates = df[df['GC']].index
            fig.add_trace(go.Scatter(
                x=gc_dates, y=df.loc[gc_dates, 'Low'] * 0.98,
                mode='markers+text', name='매수신호',
                marker=dict(symbol='triangle-up', size=15, color='red'),
                text="GOLDEN", textposition="bottom center"
            ))

            # 4. 왼쪽 매물대 바 (Volume Profile) 구현
            # 가격 구간별 빈도 계산
            counts, bins = np.histogram(df['Close'], bins=15)
            bin_centers = 0.5 * (bins[:-1] + bins[1:])
            
            for count, center in zip(counts, bin_centers):
                # 매물대 바를 왼쪽 끝에서 시작하도록 그림
                fig.add_shape(type="rect", x0=df.index[0], x1=df.index[int(count/max(counts)*20)], # 바 길이를 거래량 비례 조절
                              y0=center-(bins[1]-bins[0])/2, y1=center+(bins[1]-bins[0])/2,
                              fillcolor="gray", opacity=0.2, line_width=0)

            fig.update_layout(height=chart_height, template="plotly_white", 
                              xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
