# --- [사이드바 하단 뉴스 피드 함수] ---
def display_news_feed(market_name):
    st.sidebar.markdown("---")
    st.sidebar.subheader(f"🗞️ Byul {market_name} 실시간 뉴스")
    
    try:
        # 시장별 주요 뉴스 검색
        query = "코스피 특징주 호재" if market_name == "KOSPI" else "NASDAQ stock hot news"
        url = f"https://www.google.com/search?q={query}&tbm=nws"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 뉴스 항목 추출
        news_items = soup.select('div.SoR3S')[:5] # 최신 뉴스 5개
        
        for item in news_items:
            title = item.get_text()
            # 붉은색 포인트 이모지로 강조
            st.sidebar.markdown(f"🔴 **{title}**")
            st.sidebar.caption(f"🕒 {datetime.now().strftime('%H:%M')} 업데이트")
            st.sidebar.markdown("---")
    except:
        st.sidebar.write("뉴스 피드를 불러오는 중입니다...")

# --- [메인 실행 부분] ---
if check_password():
    # ... (기존 상단 코드 동일) ...
    
    # 사이드바 검색 및 시장 선택 하단에 뉴스 피드 배치
    display_news_feed(market)
    
    # ... (기존 차트 및 분석 코드 동일) ...
