import streamlit as st
import yfinance as yf
import pandas as pd
import time
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="AI 自動選股器", layout="wide")
st.title("🔥 AI 多維度自動選股器")

# 1. 策略選單
strategy = st.selectbox(
    "選擇今日掃描策略",
    [
        "布林通道突破 (波動轉強)",
        "均線多頭排列 (強勢趨勢)",
        "爆量長紅 (動能表態)",
        "跌深反彈 (乖離過大)",
        "創 60 日新高 (破箱噴出)",       
        "均線糾結後突破 (蓄力表態)",     
        "KD 低檔黃金交叉 (超賣轉折)",    
        "RSI 超賣回升 (擺盪尋底)",       
        "高殖利率低本益比 (價值防禦)"    
    ]
)

st.write(f"目前執行業務：**{strategy}**")

# 2. 概念股連動選單
# 2. 概念股連動選單 (🌟 終極擴充大樣本版)
CONCEPT_DICT = {
    "自訂輸入": "2330.TW, 2317.TW, 2454.TW",
    "🇹🇼 台灣前 20 大權值股 (穩健大盤)": "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2308.TW, 2881.TW, 2882.TW, 2891.TW, 3231.TW, 2886.TW, 3711.TW, 1216.TW, 2002.TW, 2884.TW, 2885.TW, 3045.TW, 2892.TW, 2303.TW, 5871.TW, 2890.TW",
    "🔥 AI 伺服器與代工 (全面版)": "2317.TW, 2382.TW, 3231.TW, 6669.TW, 2356.TW, 2376.TW, 3706.TW, 2353.TW, 2357.TW, 3035.TW, 3229.TWO, 3711.TW",
    "❄️ 散熱與液冷族群 (完整版)": "3017.TW, 3324.TW, 3036.TW, 2421.TW, 3483.TWO, 3338.TW, 3653.TW, 6230.TW, 8996.TW, 3390.TW, 3422.TW, 6806.TW",
    "⚡ 矽光子與網通 (CPO 大軍)": "3450.TW, 3081.TWO, 3163.TWO, 6442.TW, 4979.TW, 4908.TW, 3234.TWO, 3363.TW, 6451.TW, 3374.TWO, 3492.TWO, 6796.TW, 2345.TW",
    "🔋 BBU、儲能與備援電池": "6121.TWO, 3092.TW, 6282.TW, 8215.TW, 6108.TW, 6201.TW, 3211.TWO, 5309.TWO, 8038.TWO, 5425.TWO, 6781.TW",
    "💡 先進封裝 (CoWoS) 設備與材料": "3131.TWO, 6187.TWO, 2467.TW, 3583.TW, 3443.TW, 6640.TWO, 3680.TW, 5443.TWO, 6223.TW, 2360.TW, 3037.TW, 3189.TW, 8046.TW, 6515.TWO",
    "🏗️ 重電、綠能與強韌電網": "1519.TW, 1513.TW, 1503.TW, 1514.TW, 1504.TW, 1609.TW, 1605.TW, 9958.TW, 3708.TW, 6806.TW, 3712.TW",
    "🤖 機器人與智動化概念": "2359.TW, 2365.TW, 2049.TW, 1590.TW, 8374.TW, 4510.TWO, 1522.TW, 2464.TW, 8222.TWO, 4557.TW",
    "🚢 航運、航空與物流": "2603.TW, 2609.TW, 2615.TW, 2606.TW, 2636.TW, 2605.TW, 2618.TW, 2610.TW"
}

st.write("### 📝 選擇或自訂掃描名單")
selected_concept = st.selectbox("📌 快速載入熱門概念股：", list(CONCEPT_DICT.keys()))

user_input = st.text_area(
    "輸入股票代碼 (支援空格、逗號或換行分隔，台股請帶有 .TW 或 .TWO)：", 
    value=CONCEPT_DICT[selected_concept],
    height=100
)

# 解析輸入的代碼
raw_tickers = user_input.replace(',', ' ').replace('\n', ' ').split()
tickers_to_scan = list(dict.fromkeys([t.strip().upper() for t in raw_tickers if t.strip()]))

st.caption(f"💡 目前共載入 **{len(tickers_to_scan)}** 檔標的準備掃描。")

# 3. 掃描與計算核心邏輯
# ---------------------------------------------------------
# 🌟 核心：使用 Session State 記住掃描結果
# ---------------------------------------------------------
# 如果這是第一次進入網頁，先幫記憶體建立一個空的位子
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None

# 當按下掃描按鈕時，執行掃描並存入記憶體
if st.button("🚀 開始全自動掃描"):
    if not tickers_to_scan:
        st.warning("請先在上方輸入至少一檔股票代碼！")
    else:
        with st.spinner("正在逐一計算技術指標與基本面，請稍候..."):
            matched_stocks = []
            progress_bar = st.progress(0)
            total_stocks = len(tickers_to_scan)
            
            for i, ticker in enumerate(tickers_to_scan):
                try: 
                    tk = yf.Ticker(ticker)
                    info = tk.info
                    name = info.get('shortName', info.get('longName', ticker))
                    
                    # --- 基本面價值策略 ---
                    if strategy == "高殖利率低本益比 (價值防禦)":
                        pe = info.get("trailingPE", None)
                        dividend_yield = info.get("dividendYield", None)
                        
                        if pe and dividend_yield:
                            dy_percent = dividend_yield * 100
                            if pe < 20 and dy_percent >= 4.0:
                                matched_stocks.append({
                                    "代號": ticker.replace(".TW", "").replace(".TWO", ""),
                                    "名稱": name,
                                    "本益比 (P/E)": f"{pe:.1f} 倍",
                                    "現金殖利率": f"{dy_percent:.2f}%",
                                    "符合策略": strategy
                                })
                        progress_bar.progress((i + 1) / total_stocks)
                        continue

                    # --- 技術面策略 ---
                    df = tk.history(period="6mo")
                    if not df.empty and len(df) >= 60:
                        close = df['Close'].iloc[-1]
                        open_px = df['Open'].iloc[-1]
                        vol = df['Volume'].iloc[-1]

                        df['SMA5'] = df['Close'].rolling(window=5).mean()
                        df['SMA10'] = df['Close'].rolling(window=10).mean()
                        df['SMA20'] = df['Close'].rolling(window=20).mean()
                        df['SMA60'] = df['Close'].rolling(window=60).mean()
                        df['Vol_SMA5'] = df['Volume'].rolling(window=5).mean()
                        df['STD20'] = df['Close'].rolling(window=20).std()
                        df['Upper_Band'] = df['SMA20'] + (df['STD20'] * 2)

                        delta = df['Close'].diff()
                        gain = delta.where(delta > 0, 0.0)
                        loss = -delta.where(delta < 0, 0.0)
                        avg_gain = gain.rolling(window=14).mean()
                        avg_loss = loss.rolling(window=14).mean()
                        rs = avg_gain / (avg_loss + 1e-9)
                        df['RSI14'] = 100 - (100 / (1 + rs))

                        low9 = df['Low'].rolling(window=9).min()
                        high9 = df['High'].rolling(window=9).max()
                        rsv = (df['Close'] - low9) / (high9 - low9 + 1e-9) * 100
                        rsv = rsv.fillna(50)
                        
                        k_vals, d_vals = [50.0], [50.0]
                        for r in rsv:
                            k = (2/3) * k_vals[-1] + (1/3) * r
                            d = (2/3) * d_vals[-1] + (1/3) * k
                            k_vals.append(k)
                            d_vals.append(d)
                        df['K'] = k_vals[1:]
                        df['D'] = d_vals[1:]

                        sma5_now = df['SMA5'].iloc[-1]
                        sma10_now = df['SMA10'].iloc[-1]
                        sma20_now = df['SMA20'].iloc[-1]
                        sma60_now = df['SMA60'].iloc[-1]
                        upper_now = df['Upper_Band'].iloc[-1]
                        vol_sma5_prev = df['Vol_SMA5'].iloc[-2]
                        
                        k_today, k_yest = df['K'].iloc[-1], df['K'].iloc[-2]
                        d_today, d_yest = df['D'].iloc[-1], df['D'].iloc[-2]
                        rsi_today, rsi_yest = df['RSI14'].iloc[-1], df['RSI14'].iloc[-2]

                        condition_met = False
                        detail_note = ""

                        if strategy == "布林通道突破 (波動轉強)":
                            if close > upper_now:
                                condition_met = True
                                detail_note = f"突破上軌 ({upper_now:.2f})"

                        elif strategy == "均線多頭排列 (強勢趨勢)":
                            if close > sma5_now > sma20_now > sma60_now:
                                condition_met = True
                                detail_note = f"收盤 {close:.2f} 站於全均線之上"

                        elif strategy == "爆量長紅 (動能表態)":
                            if vol > (vol_sma5_prev * 2) and close > (open_px * 1.03):
                                condition_met = True
                                detail_note = f"量增 {(vol/vol_sma5_prev):.1f}倍 / 漲幅 > 3%"

                        elif strategy == "跌深反彈 (乖離過大)":
                            bias = (close - sma20_now) / sma20_now
                            if bias < -0.08:
                                condition_met = True
                                detail_note = f"負乖離 {(bias*100):.1f}%"

                        elif strategy == "創 60 日新高 (破箱噴出)":
                            high_60 = df['High'].iloc[-61:-1].max()
                            if close > high_60 and vol > vol_sma5_prev:
                                condition_met = True
                                detail_note = f"破前高 {high_60:.2f}，量增"

                        elif strategy == "均線糾結後突破 (蓄力表態)":
                            ma_max_yest = max(df['SMA5'].iloc[-2], df['SMA10'].iloc[-2], df['SMA20'].iloc[-2])
                            ma_min_yest = min(df['SMA5'].iloc[-2], df['SMA10'].iloc[-2], df['SMA20'].iloc[-2])
                            is_squeezed = ((ma_max_yest - ma_min_yest) / ma_min_yest) < 0.025
                            is_breakout = close > max(sma5_now, sma10_now, sma20_now) and (close > open_px * 1.015)
                            if is_squeezed and is_breakout:
                                condition_met = True
                                detail_note = "均線密集收斂後放量紅K上攻"

                        elif strategy == "KD 低檔黃金交叉 (超賣轉折)":
                            if k_yest < d_yest and k_today > d_today and k_yest < 25:
                                condition_met = True
                                detail_note = f"K值 {k_today:.1f} 金叉 D值 {d_today:.1f}"

                        elif strategy == "RSI 超賣回升 (擺盪尋底)":
                            if rsi_yest < 30 and rsi_today >= 30:
                                condition_met = True
                                detail_note = f"RSI 自 {rsi_yest:.1f} 回升至 {rsi_today:.1f}"

                        if condition_met:
                            matched_stocks.append({
                                "代號": ticker.replace('.TW', '').replace('.TWO', ''),
                                "名稱": name,
                                "最新收盤價": f"{close:.2f}",
                                "特徵摘要": detail_note,
                                "符合策略": strategy
                            })

                except Exception as e:
                    pass 

                progress_bar.progress((i + 1) / total_stocks)
                time.sleep(0.05)

            st.success("✅ 掃描任務完成！")
            
            # 🌟 關鍵：將掃描結果存入記憶體
            st.session_state.scan_results = matched_stocks
            st.balloons()


# ---------------------------------------------------------
# 🌟 顯示結果與 AI 區塊 (只要記憶體有東西，就會顯示出來，不怕重新整理)
# ---------------------------------------------------------
if st.session_state.scan_results is not None:
    matched_stocks = st.session_state.scan_results
    
    if matched_stocks:
        st.write(f"### 🏆 符合【{strategy}】標的清單")
        res_df = pd.DataFrame(matched_stocks)
        st.dataframe(res_df, use_container_width=True)
        
        # CSV 下載按鈕
        today_str_file = datetime.now().strftime("%Y%m%d")
        csv_data = res_df.to_csv(index=False).encode('utf-8-sig') 
        st.download_button(
            label="📥 下載完整清單 (Excel/CSV)",
            data=csv_data,
            file_name=f"強勢股清單_{strategy}_{today_str_file}.csv",
            mime="text/csv"
        )
        
        # AI 分析區塊
        st.write("---")
        st.write("### 🤖 Gemini AI 後勢策略評估")
        api_key = st.text_input("🔑 輸入 Gemini API Key 進行解讀", type="password")
        
        if st.button("✨ 產生策略後勢分析"):
            if not api_key:
                st.warning("⚠️ 請先在上方輸入您的 Gemini API Key！")
            else:
                with st.spinner("AI 正在評估市場訊號..."):
                    try:
                        stock_summary = "\n".join([f"- {s['代號']} {s['名稱']}: {s.get('特徵摘要', s.get('現金殖利率', ''))}" for s in matched_stocks])
                        prompt = f"""
                        【角色】：資深台股操盤手
                        【當前策略】：{strategy}
                        【今日選出標的】：
                        {stock_summary}

                        請針對此型態輸出 3 點結構化分析：
                        1. **族群效應**：這些股票是否屬於同族群（如 AI 伺服器、散熱、半導體），是否存在主力同步建倉訊號？
                        2. **交易指引**：採用「{strategy}」進場時，理想的停損點（如跌破哪條均線或低點）應如何設置？
                        3. **重點標的簡評**：挑選 1~2 檔具潛力的標的進行 2 行點評。
                        """
                        genai.configure(api_key=api_key)
                        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                        target_model = next((m for m in available_models if '3.8-flash' in m or '1.5-flash' in m), available_models[0])
                        model = genai.GenerativeModel(target_model)
                        res = model.generate_content(prompt)
                        
                        st.info(f"_(API 使用模型: `{target_model}`)_")
                        st.markdown(res.text)
                    except Exception as err:
                        st.error(f"API 執行錯誤：{err}")
    else:
        st.info(f"今日掃描的股票中，暫無符合【{strategy}】條件的標的。")