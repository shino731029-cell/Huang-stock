import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="AI 自動選股器", layout="wide")
st.title("🔥 AI 多維度自動選股器")

# 1. 擴充策略選單
strategy = st.selectbox(
    "選擇今日掃描策略",
    [
        "布林通道突破 (波動轉強)",
        "均線多頭排列 (強勢趨勢)",
        "爆量長紅 (動能表態)",
        "跌深反彈 (乖離過大)",
        "創 60 日新高 (破箱噴出)",       # 🌟 新增
        "均線糾結後突破 (蓄力表態)",     # 🌟 新增
        "KD 低檔黃金交叉 (超賣轉折)",    # 🌟 新增
        "RSI 超賣回升 (擺盪尋底)",       # 🌟 新增
        "高殖利率低本益比 (價值防禦)"    # 🌟 新增
    ]
)

st.write(f"目前執行業務：**{strategy}**")

stock_pool = {
    "2330.TW": "台積電", "2317.TW": "鴻海", "2454.TW": "聯發科",
    "2382.TW": "廣達", "3231.TW": "緯創", "2308.TW": "台達電",
    "2301.TW": "光寶科", "3017.TW": "奇鋐", "3324.TW": "雙鴻",
    "3450.TW": "聯鈞", "3081.TWO": "聯亞", "8299.TWO": "群聯",
    "2408.TW": "南亞科"
}

if st.button("🚀 開始全自動掃描"):
    with st.spinner("正在逐一計算技術指標與基本面，請稍候..."):
        matched_stocks = []
        progress_bar = st.progress(0)
        total_stocks = len(stock_pool)
        
        for i, (ticker, name) in enumerate(stock_pool.items()):
            try:
                tk = yf.Ticker(ticker)
                
                # --- 基本面價值策略特殊分支 ---
                if strategy == "高殖利率低本益比 (價值防禦)":
                    info = tk.info
                    pe = info.get("trailingPE", None)
                    dividend_yield = info.get("dividendYield", None) # 通常為 0.05 代表 5%
                    
                    if pe and dividend_yield:
                        dy_percent = dividend_yield * 100
                        # 條件：PE < 20 且 殖利率 >= 4.0%
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

                # --- 技術面計算邏輯 (抓取近 6 個月日 K) ---
                df = tk.history(period="6mo")
                if not df.empty and len(df) >= 60:
                    close = df['Close'].iloc[-1]
                    open_px = df['Open'].iloc[-1]
                    vol = df['Volume'].iloc[-1]

                    # 移動平均線
                    df['SMA5'] = df['Close'].rolling(window=5).mean()
                    df['SMA10'] = df['Close'].rolling(window=10).mean()
                    df['SMA20'] = df['Close'].rolling(window=20).mean()
                    df['SMA60'] = df['Close'].rolling(window=60).mean()
                    df['Vol_SMA5'] = df['Volume'].rolling(window=5).mean()

                    # 布林通道
                    df['STD20'] = df['Close'].rolling(window=20).std()
                    df['Upper_Band'] = df['SMA20'] + (df['STD20'] * 2)

                    # RSI 計算 (14日)
                    delta = df['Close'].diff()
                    gain = delta.where(delta > 0, 0.0)
                    loss = -delta.where(delta < 0, 0.0)
                    avg_gain = gain.rolling(window=14).mean()
                    avg_loss = loss.rolling(window=14).mean()
                    rs = avg_gain / (avg_loss + 1e-9)
                    df['RSI14'] = 100 - (100 / (1 + rs))

                    # KD 計算 (9, 3, 3)
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

                    # 提取最新與昨日數值
                    sma5_now = df['SMA5'].iloc[-1]
                    sma10_now = df['SMA10'].iloc[-1]
                    sma20_now = df['SMA20'].iloc[-1]
                    sma60_now = df['SMA60'].iloc[-1]
                    upper_now = df['Upper_Band'].iloc[-1]
                    vol_sma5_prev = df['Vol_SMA5'].iloc[-2]
                    
                    k_today, k_yest = df['K'].iloc[-1], df['K'].iloc[-2]
                    d_today, d_yest = df['D'].iloc[-1], df['D'].iloc[-2]
                    rsi_today, rsi_yest = df['RSI14'].iloc[-1], df['RSI14'].iloc[-2]

                    # -----------------------------------------------------
                    # 策略過濾條件
                    # -----------------------------------------------------
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
                        if bias < -0.08: # 負乖離超過 8%
                            condition_met = True
                            detail_note = f"負乖離 {(bias*100):.1f}%"

                    elif strategy == "創 60 日新高 (破箱噴出)":
                        high_60 = df['High'].iloc[-61:-1].max() # 排除今日的前60日高點
                        if close > high_60 and vol > vol_sma5_prev:
                            condition_met = True
                            detail_note = f"破前高 {high_60:.2f}，量增"

                    elif strategy == "均線糾結後突破 (蓄力表態)":
                        # 檢查 5, 10, 20 日線在昨日的最大與最小值差距是否小於 2.5%
                        ma_max_yest = max(df['SMA5'].iloc[-2], df['SMA10'].iloc[-2], df['SMA20'].iloc[-2])
                        ma_min_yest = min(df['SMA5'].iloc[-2], df['SMA10'].iloc[-2], df['SMA20'].iloc[-2])
                        is_squeezed = ((ma_max_yest - ma_min_yest) / ma_min_yest) < 0.025
                        is_breakout = close > max(sma5_now, sma10_now, sma20_now) and (close > open_px * 1.015)
                        if is_squeezed and is_breakout:
                            condition_met = True
                            detail_note = "均線密集收斂後放量紅K上攻"

                    elif strategy == "KD 低檔黃金交叉 (超賣轉折)":
                        # 條件：昨日 K<D，今日 K>D，且昨日 K < 25 (超賣區)
                        if k_yest < d_yest and k_today > d_today and k_yest < 25:
                            condition_met = True
                            detail_note = f"K值 {k_today:.1f} 金叉 D值 {d_today:.1f}"

                    elif strategy == "RSI 超賣回升 (擺盪尋底)":
                        # 條件：昨日 RSI < 30，今日突破向上站上 30
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

        if matched_stocks:
            st.write(f"### 🏆 符合【{strategy}】標的清單")
            res_df = pd.DataFrame(matched_stocks)
            st.dataframe(res_df, use_container_width=True)
            st.balloons()
            
            # --- AI 呼叫整合模組 ---
            st.write("---")
            st.write("### 🤖 Gemini AI 後勢策略評估")
            api_key = st.text_input("🔑 輸入 Gemini API Key 進行解讀", type="password")
            
            if api_key and st.button("✨ 產生策略後勢分析"):
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
                        st.markdown(res.text)
                    except Exception as err:
                        st.error(f"API 執行錯誤：{err}")
        else:
            st.info(f"今日掃描的股票中，暫無符合【{strategy}】條件的標的。")