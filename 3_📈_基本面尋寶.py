import streamlit as st
import yfinance as yf
import pandas as pd
import time
from datetime import datetime

st.set_page_config(page_title="基本面尋寶", layout="wide")
st.title("📈 基本面尋寶 (自訂財務濾網)")

st.write("透過設定嚴格的財務指標，從市場中挖掘具備長線投資價值的穩健企業。")

# 1. 設定財務濾網條件
st.sidebar.header("⚙️ 設定財務濾網")
min_roe = st.sidebar.slider("最低 ROE (股東權益報酬率) %", min_value=0, max_value=30, value=15, step=1)
min_yoy = st.sidebar.slider("最低營收年增率 (YoY) %", min_value=-20, max_value=50, value=10, step=5)
max_debt_ratio = st.sidebar.slider("最高負債比率 %", min_value=10, max_value=100, value=60, step=5)
min_yield = st.sidebar.slider("最低預估殖利率 %", min_value=0.0, max_value=10.0, value=4.0, step=0.5)

# 2. 概念股連動選單 (與自動選股器共用或可自訂)
CONCEPT_DICT = {
    "🇹🇼 台灣前 20 大權值股 (穩健大盤)": "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2308.TW, 2881.TW, 2882.TW, 2891.TW, 3231.TW, 2886.TW, 3711.TW, 1216.TW, 2002.TW, 2884.TW, 2885.TW, 3045.TW, 2892.TW, 2303.TW, 5871.TW, 2890.TW",
    "🔥 AI 伺服器與代工 (全面版)": "2317.TW, 2382.TW, 3231.TW, 6669.TW, 2356.TW, 2376.TW, 3706.TW, 2353.TW, 2357.TW, 3035.TW, 3229.TWO, 3711.TW",
    "自訂輸入": "2330.TW, 2317.TW"
}

st.write("### 📝 選擇掃描名單")
selected_concept = st.selectbox("📌 快速載入名單：", list(CONCEPT_DICT.keys()))

user_input = st.text_area(
    "輸入股票代碼：", 
    value=CONCEPT_DICT[selected_concept],
    height=100
)

raw_tickers = user_input.replace(',', ' ').replace('\n', ' ').split()
tickers_to_scan = list(dict.fromkeys([t.strip().upper() for t in raw_tickers if t.strip()]))

# 初始化 session state
if 'fundamental_results' not in st.session_state:
    st.session_state.fundamental_results = None

# 3. 掃描與計算核心邏輯
if st.button("🚀 開始基本面掃描"):
    if not tickers_to_scan:
        st.warning("請先輸入股票代碼！")
    else:
        with st.spinner("正在下載財報數據，這可能需要一點時間..."):
            matched_stocks = []
            progress_bar = st.progress(0)
            total_stocks = len(tickers_to_scan)
            
            for i, ticker in enumerate(tickers_to_scan):
                try:
                    tk = yf.Ticker(ticker)
                    info = tk.info
                    name = info.get('shortName', info.get('longName', ticker))
                    
                    # 取得基本面數據
                    roe = info.get('returnOnEquity', 0)
                    revenue_growth = info.get('revenueGrowth', 0)
                    debt_to_equity = info.get('debtToEquity', 0) # yfinance 給的是百分比數字，例如 50 代表 50%
                    dividend_yield = info.get('dividendYield', 0)

                    # 處理 None 值並轉換格式
                    roe = roe * 100 if roe else 0
                    revenue_growth = revenue_growth * 100 if revenue_growth else 0
                    debt_ratio = debt_to_equity if debt_to_equity else 100 # 如果抓不到，預設為高負債
                    dy_percent = dividend_yield * 100 if dividend_yield else 0

                    # 判斷是否符合所有濾網條件
                    if (roe >= min_roe and 
                        revenue_growth >= min_yoy and 
                        debt_ratio <= max_debt_ratio and 
                        dy_percent >= min_yield):
                        
                        matched_stocks.append({
                            "代號": ticker.replace(".TW", "").replace(".TWO", ""),
                            "名稱": name,
                            "ROE (%)": f"{roe:.2f}",
                            "營收年增率 (%)": f"{revenue_growth:.2f}",
                            "負債比率 (%)": f"{debt_ratio:.2f}",
                            "殖利率 (%)": f"{dy_percent:.2f}"
                        })

                except Exception as e:
                    pass # 忽略抓不到資料的股票

                progress_bar.progress((i + 1) / total_stocks)
                time.sleep(0.1) # 避免請求過快被阻擋

            st.success("✅ 掃描任務完成！")
            st.session_state.fundamental_results = matched_stocks
            st.balloons()

# 4. 顯示結果與下載
if st.session_state.fundamental_results is not None:
    matched_stocks = st.session_state.fundamental_results
    
    if matched_stocks:
        st.write("### 🏆 財務體質優良清單")
        res_df = pd.DataFrame(matched_stocks)
        st.dataframe(res_df, use_container_width=True)
        
        # 下載 CSV 功能
        today_str_file = datetime.now().strftime("%Y%m%d")
        csv_data = res_df.to_csv(index=False).encode('utf-8-sig') 
        st.download_button(
            label="📥 下載基本面清單 (Excel/CSV)",
            data=csv_data,
            file_name=f"基本面優良股_{today_str_file}.csv",
            mime="text/csv"
        )
    else:
        st.info("目前的條件太嚴格了，今天掃描的股票中沒有符合全部條件的公司。試著放寬一點標準吧！")