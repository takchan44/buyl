import streamlit as st
import FinanceDataReader as fdr
import pandas as pd
import requests
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime

# --- [1. 보안 설정] ---
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

# --- [2. 실시간 뉴스 엔진 (강화형)] ---
def get_live_news_feed(name, is_us=False):
    news_list = []
    try:
        query = f"{name} stock" if is_us else f"{name} 주가 특징주"
        url = f"https://www.google.com/search?q={query}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 구글 뉴스 제목 추출 로직 보강
        items = soup.find_all('div', {'role': 'heading'}) or soup.select('h3')
        for item in items[:8]: # 뉴스 8개까지 수집
            title = item.get_text().strip()
            if len(title) > 10:
                news_list.append(title)
    except:
        pass
    return news_list

# --- [3. 메인 실행부] ---
if check_password():
    # 사이드바 설정
    st.sidebar.title("⭐️ Byul Search")
    market = st.sidebar.radio("시장 선택", ["KOSPI", "NASDAQ"])
    chart_height = st.sidebar.slider("📊 그래프 높이 조절", 400, 1000, 700)
    
    @st.cache_data
    def get_full_list(m): return fdr.StockListing(m)
    
    full_list = get_full_list(market)
    search = st.sidebar.text_input("🔍 종목명/티커 검색").upper()
    
    if search:
        filtered = full_list[full_list['Name' if market=="KOSPI" else 'Symbol'].str.contains(search, na=False)]
    else: filtered = full_list.head(100)
    
    selected = st.sidebar.selectbox("종목 선택", filtered['Name' if market=="KOSPI" else 'Symbol'].tolist())

    # --- [왼쪽 사이드바 하단 뉴스 배치] ---
    if selected:
        st.sidebar.markdown("---")
        st.sidebar.subheader(f"🗞️ {selected} 실시간 뉴스")
        live_news = get_live_news_feed(selected, is_us=(market=="NASDAQ"))
        
        if live_news:
            for n in live_news:
                st.sidebar.markdown(f"🔴 **{n}**")
                st.sidebar.caption(f"🕒 {datetime.now().strftime('%H:%M')} 확인")
                st.sidebar.markdown("---")
        else:
            st.sidebar.warning("실시간 뉴스를 불러올 수 없습니다. 다시 시도해 주세요.")

    # --- [오른쪽 메인 콘텐츠 영역] ---
    if selected:
        row = filtered[filtered['Name' if market=="KOSPI" else 'Symbol'] == selected]
        code = row['Code' if market=="KOSPI" else 'Symbol'].values[0]
        df = fdr.DataReader(code).tail(120)
        
        # 지표 계산
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['GC'] = (df['MA5'] >= df['MA20']) & (df['MA5'].shift(1) < df['MA20'].shift(1))

        # 메인 차트와 뉴스 요약 레이아웃
        col_summary, col_main = st.columns([1, 4]) # 요약창을 좁게, 차트를 넓게

        with col_summary:
            st.markdown("### 🤖 분석 요약")
            curr_price = df.iloc[-1]['Close']
            prev_price = df.iloc[-2]['Close']
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            st.metric(label="현재가", value=f"{curr_price:,}", delta=f"{change_pct:.2f}%")
            
            if df.iloc[-1]['GC']:
                st.error("🚨 GOLDEN CROSS 발생!")
            else:
                st.info("정배열 추세 유지 중")

        with col_main:
            # --- 차트 구성 ---
            fig = make_subplots(specs=[[{"secondary_y": True}]])

            # 1. 캔들스틱
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="주가", increasing_line_color='#f44336', decreasing_line_color='#2196f3'
            ))

            # 2. 이동평균선
            fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name="5일선", line=dict(color='orange', width=1.5)))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name="20일선", line=dict(color='green', width=1.5)))

            # 3. 골든크로스 화살표 (그래프 안)
            gc_dates = df[df['GC']].index
            if not gc_dates.empty:
                fig.add_trace(go.Scatter(
                    x=gc_dates, y=df.loc[gc_dates, 'Low'] * 0.97,
                    mode='markers+text', name='매수타점',
                    marker=dict(symbol='triangle-up', size=18, color='red'),
                    text="★GOLDEN", textposition="bottom center"
                ))

            # 4. 왼쪽 가로 매물대 바 (Volume Profile)
            counts, bins = np.histogram(df['Close'], bins=20)
            bin_centers = 0.5 * (bins[:-1] + bins[1:])
            max_count = max(counts)
            
            for count, center in zip(counts, bin_centers):
                # 바 길이를 인덱스 기간의 15% 정도로 제한하여 왼쪽 배치
                bar_len = int(len(df) * 0.15 * (count / max_count))
                fig.add_shape(type="rect", 
                              x0=df.index[0], x1=df.index[bar_len] if bar_len > 0 else df.index[0],
                              y0=center-(bins[1]-bins[0])/2, y1=center+(bins[1]-bins[0])/2,
                              fillcolor="gray", opacity=0.25, line_width=0)

            fig.update_layout(height=chart_height, template="plotly_white", 
                              xaxis_rangeslider_visible=False, 
                              margin=dict(l=10, r=10, t=10, b=10),
                              legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True)
