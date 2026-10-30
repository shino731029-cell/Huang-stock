import streamlit as st
import yfinance as yf
import pandas as pd
import time
import google.generativeai as genai
from datetime import datetime
import plotly.graph_objects as go
import gc

st.set_page_config(page_title="AI 自動選股器", layout="wide")

# ---------------------------------------------------------
# 🌟 大盤即時溫度計
# ---------------------------------------------------------
@st.cache_data(ttl=300)
def get_market_index(ticker_symbol):
    try:
        tk = yf.Ticker(ticker_symbol)
        df = tk.history(period="2d")
        if len(df) >= 2:
            current_price = df['Close'].iloc[-1]
            prev_price = df['Close'].iloc[-2]
            return current_price, current_price - prev_price, ((current_price - prev_price) / prev_price) * 100
        elif len(df) == 1:
            return df['Close'].iloc[-1], 0.0, 0.0
        return None, None, None
    except Exception:
        return None, None, None

st.title("🔥 AI 多維度自動選股器 (策略分類版)")
st.write("### 📊 大盤即時溫度計")

col1, col2, col3 = st.columns(3)
twii_price, twii_chg, twii_pct = get_market_index("^TWII")
if twii_price is not None:
    col1.metric("🇹🇼 台股加權指數 (大盤)", f"{twii_price:,.2f}", f"{twii_chg:,.2f} ({twii_pct:.2f}%)", delta_color="inverse")
else:
    col1.metric("🇹🇼 台股加權指數", "資料讀取中...", "-")

otc_price, otc_chg, otc_pct = get_market_index("^TWOII")
if otc_price is not None:
    col2.metric("📈 櫃買指數 (OTC)", f"{otc_price:,.2f}", f"{otc_chg:,.2f} ({otc_pct:.2f}%)", delta_color="inverse")
else:
    col2.metric("📈 櫃買指數 (OTC)", "資料讀取中...", "-")

sox_price, sox_chg, sox_pct = get_market_index("^SOX")
if sox_price is not None:
    col3.metric("🇺🇸 費城半導體指數", f"{sox_price:,.2f}", f"{sox_chg:,.2f} ({sox_pct:.2f}%)", delta_color="inverse")
else:
    col3.metric("🇺🇸 費城半導體指數", "資料讀取中...", "-")

st.write("---")

# ---------------------------------------------------------
# 1. 策略分類字典與選單 (🌟 全新改版)
# ---------------------------------------------------------
STRATEGY_DICT = {
    "🚀 動能與突破 (攻擊型)": [
        "布林通道突破 (波動轉強)",
        "爆量長紅 (動能表態)",
        "創 60 日新高 (破箱噴出)",
        "向上跳空缺口不補 (強勢表態)",
        "均線黃金交叉 (短線轉強)" # 🆕 新增
    ],
    "📈 趨勢與波段 (順勢型)": [
        "均線多頭排列 (強勢趨勢)",
        "均線糾結後突破 (蓄力表態)",
        "MACD 零軸上金叉 (波段起漲)",
        "MACD 柱狀圖轉紅 (初步翻多)" # 🆕 新增
    ],
    "🛡️ 抄底與反轉 (逆勢型)": [
        "跌深反彈 (負乖離過大)",
        "KD 低檔黃金交叉 (超賣轉折)",
        "RSI 超賣回升 (擺盪尋底)",
        "破底翻 (下軌假跌破)" # 🆕 新增
    ],
    "🏦 價值與基本面 (防禦型)": [
        "高殖利率低本益比 (價值防禦)",
        "低股價淨值比 PB < 1.2 (低基期尋寶)",
        "高 ROE 優質股 (護城河防禦)" # 🆕 新增
    ]
}

st.write("### ⚙️ 選擇今日掃描策略")
col_cat, col_strat = st.columns(2)
with col_cat:
    selected_category = st.selectbox("1️⃣ 選擇策略類別：", list(STRATEGY_DICT.keys()))
with col_strat:
    strategy = st.selectbox("2️⃣ 選擇具體策略：", STRATEGY_DICT[selected_category])

st.write("---")

# ---------------------------------------------------------
# 產業板塊名單
# ---------------------------------------------------------
CONCEPT_DICT = {
    "自訂輸入": "2330.TW, 2317.TW, 2454.TW",
    "🇹🇼 台灣前 20 大權值股": "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2308.TW, 2881.TW, 2882.TW, 2891.TW, 3231.TW, 2886.TW",
    "🔥 AI 伺服器與代工": "2317.TW, 2382.TW, 3231.TW, 6669.TW, 2356.TW, 2376.TW, 3706.TW, 2353.TW",
    "❄️ 散熱與液冷族群": "3017.TW, 3324.TW, 3036.TW, 2421.TW, 3483.TWO, 3338.TW",
    "⚡ 矽光子與網通 (CPO)": "3450.TW, 3081.TWO, 3163.TWO, 6442.TW, 4979.TW, 4908.TW",
    "🧠 AI 矽智財與 ASIC": "3443.TW, 3661.TW, 3529.TW, 6643.TWO, 3035.TW, 6531.TW, 6533.TW",
    "⚙️ AI 伺服器機殼與導軌": "8210.TW, 2059.TW, 3013.TW, 3693.TW, 5236.TWO",
    "🤖 輝達機器人與視覺智能": "2359.TW, 2365.TW, 6188.TWO, 6215.TW, 2464.TW",
    "⬛ FOPLP 面板級封裝": "3481.TW, 2409.TW, 3583.TW, 3131.TWO, 6640.TWO, 6239.TW",
    "🛰️ 低軌衛星與太空通訊": "2314.TW, 3491.TW, 6271.TW, 3311.TW, 2383.TW, 6285.TW, 3466.TWO, 2313.TW",
    "🚘 無人駕駛與車用電子": "2308.TW, 6282.TW, 3552.TW, 2231.TW, 1319.TW, 3346.TW, 5425.TWO, 2497.TW",
    "🧬 生技醫療與 CDMO": "6547.TW, 4743.TW, 1795.TW, 6472.TW, 6446.TWO, 4147.TWO, 1762.TW"
}

st.write("### 📝 選擇掃描名單")
selected_concept = st.selectbox("📌 快速載入熱門概念股 (雲端為求穩定已精簡數量)：", list(CONCEPT_DICT.keys()))
user_input = st.text_area("輸入股票代碼：", value=CONCEPT_DICT[selected_concept], height=80)
raw_tickers = user_input.replace(',', ' ').replace('\n', ' ').split()
tickers_to_scan = list(dict.fromkeys([t.strip().upper() for t in raw_tickers if t.strip()]))[:10]
st.caption(f"💡 雲端穩定版每次最多掃描 10 檔。目前載入 **{len(tickers_to_scan)}** 檔標的。")

if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None

# ---------------------------------------------------------
# 2. 掃描核心邏輯 (加入全新策略演算法)
# ---------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def run_scan(tickers, selected_strategy):
    results = []
    for ticker in tickers:
        try: 
            tk = yf.Ticker(ticker)
            info = tk.info
            name = info.get('shortName', info.get('longName', ticker))
            
            # --- 基本面策略群 ---
            if selected_strategy == "高殖利率低本益比 (價值防禦)":
                pe, dy = info.get("trailingPE"), info.get("dividendYield")
                if pe and dy and pe < 20 and dy * 100 >= 4.0:
                    results.append({"代號": ticker.replace(".TW", "").replace(".TWO", ""), "名稱": name, "最新收盤價": "-", "特徵摘要": f"PE:{pe:.1f}倍, 殖利率:{dy*100:.2f}%", "符合策略": selected_strategy, "新聞輿情": "無", "原始代號": ticker})
                continue
                
            elif selected_strategy == "低股價淨值比 PB < 1.2 (低基期尋寶)":
                pb = info.get("priceToBook")
                if pb and 0 < pb < 1.2:
                    results.append({"代號": ticker.replace(".TW", "").replace(".TWO", ""), "名稱": name, "最新收盤價": "-", "特徵摘要": f"股價淨值比 PB: {pb:.2f}倍", "符合策略": selected_strategy, "新聞輿情": "無", "原始代號": ticker})
                continue
                
            elif selected_strategy == "高 ROE 優質股 (護城河防禦)":
                roe, pb = info.get("returnOnEquity"), info.get("priceToBook")
                if roe and pb and roe > 0.15 and 0 < pb < 3.0:
                    results.append({"代號": ticker.replace(".TW", "").replace(".TWO", ""), "名稱": name, "最新收盤價": "-", "特徵摘要": f"ROE: {roe*100:.1f}%, PB: {pb:.1f}倍", "符合策略": selected_strategy, "新聞輿情": "無", "原始代號": ticker})
                continue

            # --- 技術面策略群 ---
            df = tk.history(period="3mo")
            if df.empty or len(df) < 60: continue

            close, open_px, vol = df['Close'].iloc[-1], df['Open'].iloc[-1], df['Volume'].iloc[-1]
            high_yest = df['High'].iloc[-2]
            low_today = df['Low'].iloc[-1]
            
            df['SMA5'] = df['Close'].rolling(5).mean()
            df['SMA20'] = df['Close'].rolling(20).mean()
            df['SMA60'] = df['Close'].rolling(60).mean()
            df['Vol_SMA5'] = df['Volume'].rolling(5).mean()
            df['STD20'] = df['Close'].rolling(20).std()
            df['Upper_Band'] = df['SMA20'] + (df['STD20'] * 2)
            df['Lower_Band'] = df['SMA20'] - (df['STD20'] * 2) # 🆕 計算下軌

            delta = df['Close'].diff()
            rs = delta.where(delta > 0, 0.0).rolling(14).mean() / (-delta.where(delta < 0, 0.0).rolling(14).mean() + 1e-9)
            df['RSI14'] = 100 - (100 / (1 + rs))

            ema12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema26 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = ema12 - ema26
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal'] # 🆕 計算柱狀圖

            sma5_now, sma20_now, sma60_now = df['SMA5'].iloc[-1], df['SMA20'].iloc[-1], df['SMA60'].iloc[-1]
            sma5_yest, sma20_yest = df['SMA5'].iloc[-2], df['SMA20'].iloc[-2]
            upper_now, lower_now = df['Upper_Band'].iloc[-1], df['Lower_Band'].iloc[-1]
            vol_sma5_prev = df['Vol_SMA5'].iloc[-2]
            rsi_today, rsi_yest = df['RSI14'].iloc[-1], df['RSI14'].iloc[-2]
            macd_today, macd_yest = df['MACD'].iloc[-1], df['MACD'].iloc[-2]
            sig_today, sig_yest = df['MACD_Signal'].iloc[-1], df['MACD_Signal'].iloc[-2]
            hist_today, hist_yest = df['MACD_Hist'].iloc[-1], df['MACD_Hist'].iloc[-2]

            condition_met, detail_note = False, ""
            
            # 動能與突破
            if selected_strategy == "布林通道突破 (波動轉強)" and close > upper_now: condition_met, detail_note = True, f"突破上軌 ({upper_now:.2f})"
            elif selected_strategy == "爆量長紅 (動能表態)" and vol > (vol_sma5_prev * 2) and close > (open_px * 1.03): condition_met, detail_note = True, f"量增 {(vol/vol_sma5_prev):.1f}倍"
            elif selected_strategy == "創 60 日新高 (破箱噴出)" and close > df['High'].iloc[-61:-1].max() and vol > vol_sma5_prev: condition_met, detail_note = True, "破前高且量增"
            elif selected_strategy == "向上跳空缺口不補 (強勢表態)" and low_today > (high_yest * 1.015) and close > open_px: condition_met, detail_note = True, "跳空缺口 > 1.5% 收紅"
            elif selected_strategy == "均線黃金交叉 (短線轉強)" and sma5_yest <= sma20_yest and sma5_now > sma20_now: condition_met, detail_note = True, "5MA 向上突破 20MA"
            
            # 趨勢與波段
            elif selected_strategy == "均線多頭排列 (強勢趨勢)" and close > sma5_now > sma20_now > sma60_now: condition_met, detail_note = True, "站於全均線之上"
            elif selected_strategy == "均線糾結後突破 (蓄力表態)" and ((max(sma5_yest, sma20_yest) - min(sma5_yest, sma20_yest)) / min(sma5_yest, sma20_yest) < 0.025) and close > max(sma5_now, sma20_now) and (close > open_px * 1.015): condition_met, detail_note = True, "均線收斂後放量紅K"
            elif selected_strategy == "MACD 零軸上金叉 (波段起漲)" and macd_yest < sig_yest and macd_today > sig_today and macd_today > 0: condition_met, detail_note = True, f"MACD {macd_today:.2f} 金叉"
            elif selected_strategy == "MACD 柱狀圖轉紅 (初步翻多)" and hist_yest <= 0 and hist_today > 0: condition_met, detail_note = True, "柱狀圖由綠翻紅"

            # 抄底與反轉
            elif selected_strategy == "跌深反彈 (負乖離過大)" and ((close - sma20_now) / sma20_now) < -0.08: condition_met, detail_note = True, "負乖離 > 8%"
            elif selected_strategy == "RSI 超賣回升 (擺盪尋底)" and rsi_yest < 30 and rsi_today >= 30: condition_met, detail_note = True, f"RSI 回升至 {rsi_today:.1f}"
            elif selected_strategy == "破底翻 (下軌假跌破)" and low_today < lower_now and close > lower_now and close > open_px: condition_met, detail_note = True, "跌破下軌後收紅站回"

            if condition_met:
                news_titles = ""
                try:
                    for news in tk.news[:2]:
                        news_titles += f"[{datetime.fromtimestamp(news['providerPublishTime']).strftime('%m/%d')}] {news['title']}\n"
                except: news_titles = "無相關新聞"
                
                results.append({"代號": ticker.replace('.TW', '').replace('.TWO', ''), "名稱": name, "最新收盤價": f"{close:.2f}", "特徵摘要": detail_note, "符合策略": selected_strategy, "新聞輿情": news_titles or "無", "原始代號": ticker})
        except Exception: pass
        time.sleep(0.3)
    return results

if st.button("🚀 開始全自動掃描 (策略分類版)"):
    if not tickers_to_scan:
        st.warning("請先輸入股票代碼！")
    else:
        with st.spinner(f"系統極速運算中... (目前選擇：{strategy})"):
            st.session_state.scan_results = run_scan(tickers_to_scan, strategy)
            st.success("✅ 掃描任務完成！")
            st.balloons()
            gc.collect()

# ---------------------------------------------------------
# 3. 顯示結果、畫圖與 AI 分析
# ---------------------------------------------------------
if st.session_state.get('scan_results') is not None:
    matched_stocks = st.session_state.scan_results
    if matched_stocks:
        st.write(f"### 🏆 符合【{strategy}】標的清單")
        res_df = pd.DataFrame(matched_stocks)
        st.dataframe(res_df.drop(columns=['新聞輿情', '原始代號'], errors='ignore'), use_container_width=True)
        
        today_str_file = datetime.now().strftime("%Y%m%d")
        st.download_button("📥 下載完整清單 (CSV)", res_df.to_csv(index=False).encode('utf-8-sig'), f"強勢股清單_{today_str_file}.csv", "text/csv")
        
        st.write("---")
        st.write("### 📈 個股技術線型 (互動圖表)")
        chart_options = {f"{s['代號']} {s['名稱']}": s['原始代號'] for s in matched_stocks}
        selected_label = st.selectbox("🔍 選擇標的查看詳細線圖：", list(chart_options.keys()))

        if selected_label:
            target_ticker = chart_options[selected_label]
            tk_chart = yf.Ticker(target_ticker)
            df_chart = tk_chart.history(period="6mo")
            if not df_chart.empty:
                df_chart['SMA20'] = df_chart['Close'].rolling(20).mean()
                df_chart['STD20'] = df_chart['Close'].rolling(20).std()
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], increasing_line_color='#ef5350', decreasing_line_color='#26a69a', name='K線'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA20'], line=dict(color='blue', width=1.5), name='20MA (月線)'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA20'] + (df_chart['STD20'] * 2), line=dict(color='rgba(173,216,230,0.8)', dash='dot'), name='布林上軌'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA20'] - (df_chart['STD20'] * 2), line=dict(color='rgba(173,216,230,0.8)', dash='dot'), name='布林下軌'))
                fig.update_layout(title=f"【{selected_label}】 近半年走勢圖", xaxis_rangeslider_visible=False, height=450, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

        st.write("---")
        st.write("### 🤖 Gemini AI 新聞輿情與策略評估")
        api_key = st.text_input("🔑 輸入 Gemini API Key 進行輿情解讀", type="password")
        if st.button("✨ 產生輿情雷達與分析"):
            if api_key:
                with st.spinner("AI 正在評估訊號..."):
                    try:
                        stock_summary = "".join([f"■ 【{s['代號']} {s['名稱']}】 收盤價: {s['最新收盤價']} | 特徵: {s.get('特徵摘要', '')}\n近期新聞：\n{s.get('新聞輿情', '無')}\n\n" for s in matched_stocks])
                        prompt = f"策略：{strategy} (屬於 {selected_category})\n日期：{datetime.now().strftime('%Y/%m/%d')}\n標的與新聞：\n{stock_summary}\n請分析：1.族群效應 2.訊號真偽(搭配新聞) 3.停損建議"
                        
                        genai.configure(api_key=api_key)
                        fallback_models = ['gemini-3.8-flash', 'gemini-1.5-flash', 'gemini-pro']
                        success = False
                        
                        for model_name in fallback_models:
                            try:
                                model = genai.GenerativeModel(model_name)
                                res = model.generate_content(prompt)
                                st.info(f"_(✅ 成功配對最新模型: `{model_name}`)_")
                                st.markdown(res.text)
                                success = True
                                break 
                            except Exception:
                                continue 
                                
                        if not success:
                            st.error("❌ 所有備用模型皆呼叫失敗。請確認您的 API Key 權限。")
                    except Exception as err:
                        st.error(f"API 系統內部錯誤：{err}")
            else:
                st.warning("⚠️ 請輸入 API Key！")
    else:
        st.info("暫無符合條件標的。")
