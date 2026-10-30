import streamlit as st
import yfinance as yf
import pandas as pd
import time
import google.generativeai as genai
from datetime import datetime
import plotly.graph_objects as go
import gc

st.set_page_config(page_title="AI 自動選股器", layout="wide")

# --- 大盤溫度計 ---
@st.cache_data(ttl=300) # 快取 5 分鐘
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

st.title("🔥 AI 多維度自動選股器 (雲端穩定版)")
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

# --- 策略與名單 ---
strategy = st.selectbox(
    "選擇今日掃描策略",
    ["布林通道突破 (波動轉強)", "均線多頭排列 (強勢趨勢)", "爆量長紅 (動能表態)", "跌深反彈 (乖離過大)", "創 60 日新高 (破箱噴出)", "均線糾結後突破 (蓄力表態)", "KD 低檔黃金交叉 (超賣轉折)", "RSI 超賣回升 (擺盪尋底)", "高殖利率低本益比 (價值防禦)"]
)

CONCEPT_DICT = {
    "自訂輸入": "2330.TW, 2317.TW, 2454.TW",
    "🇹🇼 台灣前 20 大權值股": "2330.TW, 2317.TW, 2454.TW, 2382.TW, 2308.TW, 2881.TW, 2882.TW, 2891.TW, 3231.TW, 2886.TW",
    "🔥 AI 伺服器與代工": "2317.TW, 2382.TW, 3231.TW, 6669.TW, 2356.TW, 2376.TW, 3706.TW, 2353.TW",
    "❄️ 散熱與液冷族群": "3017.TW, 3324.TW, 3036.TW, 2421.TW, 3483.TWO, 3338.TW",
    "⚡ 矽光子與網通 (CPO)": "3450.TW, 3081.TWO, 3163.TWO, 6442.TW, 4979.TW, 4908.TW",
    
    # 👇 以下為全新擴充的 AI 供應鏈次族群
    "🧠 AI 矽智財與 ASIC (高本益比區)": "3443.TW, 3661.TW, 3529.TW, 6643.TWO, 3035.TW, 6531.TW, 6533.TW",
    "💻 AI PC 與邊緣運算 (消費端 AI)": "2353.TW, 2357.TW, 2324.TW, 2377.TW, 2454.TW, 4938.TW",
    "⚙️ AI 伺服器機殼與導軌 (機構件)": "8210.TW, 2059.TW, 3013.TW, 3693.TW, 5236.TWO",
    "🧪 AI 測試設備與驗證介面": "2360.TW, 2449.TW, 6223.TW, 6515.TWO, 6683.TWO",
    "🤖 輝達機器人與視覺智能": "2359.TW, 2365.TW, 6188.TWO, 6215.TW, 2464.TW",
}

selected_concept = st.selectbox("📌 快速載入熱門概念股 (雲端為求穩定已精簡數量)：", list(CONCEPT_DICT.keys()))
user_input = st.text_area("輸入股票代碼：", value=CONCEPT_DICT[selected_concept], height=80)
raw_tickers = user_input.replace(',', ' ').replace('\n', ' ').split()
tickers_to_scan = list(dict.fromkeys([t.strip().upper() for t in raw_tickers if t.strip()]))[:10] # 極限壓在 10 檔
st.caption(f"💡 雲端穩定版每次最多掃描 10 檔。目前載入 **{len(tickers_to_scan)}** 檔標的。")

# --- 核心快取選股函數 ---
@st.cache_data(ttl=3600, show_spinner=False) # 快取 1 小時，避免重複運算
def run_scan(tickers, selected_strategy):
    results = []
    for ticker in tickers:
        try: 
            tk = yf.Ticker(ticker)
            info = tk.info
            name = info.get('shortName', info.get('longName', ticker))
            
            if selected_strategy == "高殖利率低本益比 (價值防禦)":
                pe, dy = info.get("trailingPE"), info.get("dividendYield")
                if pe and dy and pe < 20 and dy * 100 >= 4.0:
                    results.append({"代號": ticker.replace(".TW", "").replace(".TWO", ""), "名稱": name, "最新收盤價": "-", "特徵摘要": f"PE:{pe:.1f}倍, 殖利率:{dy*100:.2f}%", "符合策略": selected_strategy, "新聞輿情": "無", "原始代號": ticker})
                continue

            df = tk.history(period="3mo") # 只抓 3 個月
            if df.empty or len(df) < 60: continue

            close, open_px, vol = df['Close'].iloc[-1], df['Open'].iloc[-1], df['Volume'].iloc[-1]
            df['SMA5'] = df['Close'].rolling(5).mean()
            df['SMA20'] = df['Close'].rolling(20).mean()
            df['SMA60'] = df['Close'].rolling(60).mean()
            df['Vol_SMA5'] = df['Volume'].rolling(5).mean()
            df['STD20'] = df['Close'].rolling(20).std()
            df['Upper_Band'] = df['SMA20'] + (df['STD20'] * 2)

            delta = df['Close'].diff()
            rs = delta.where(delta > 0, 0.0).rolling(14).mean() / (-delta.where(delta < 0, 0.0).rolling(14).mean() + 1e-9)
            df['RSI14'] = 100 - (100 / (1 + rs))

            sma5_now, sma20_now, sma60_now = df['SMA5'].iloc[-1], df['SMA20'].iloc[-1], df['SMA60'].iloc[-1]
            upper_now, vol_sma5_prev = df['Upper_Band'].iloc[-1], df['Vol_SMA5'].iloc[-2]
            rsi_today, rsi_yest = df['RSI14'].iloc[-1], df['RSI14'].iloc[-2]

            condition_met, detail_note = False, ""
            if selected_strategy == "布林通道突破 (波動轉強)" and close > upper_now: condition_met, detail_note = True, f"突破上軌 ({upper_now:.2f})"
            elif selected_strategy == "均線多頭排列 (強勢趨勢)" and close > sma5_now > sma20_now > sma60_now: condition_met, detail_note = True, f"收盤 {close:.2f} 站於全均線之上"
            elif selected_strategy == "爆量長紅 (動能表態)" and vol > (vol_sma5_prev * 2) and close > (open_px * 1.03): condition_met, detail_note = True, f"量增 {(vol/vol_sma5_prev):.1f}倍"
            elif selected_strategy == "跌深反彈 (乖離過大)" and ((close - sma20_now) / sma20_now) < -0.08: condition_met, detail_note = True, "負乖離 > 8%"
            elif selected_strategy == "RSI 超賣回升 (擺盪尋底)" and rsi_yest < 30 and rsi_today >= 30: condition_met, detail_note = True, f"RSI 回升至 {rsi_today:.1f}"

            if condition_met:
                news_titles = ""
                try:
                    for news in tk.news[:2]: # 新聞只抓 2 則
                        news_titles += f"[{datetime.fromtimestamp(news['providerPublishTime']).strftime('%m/%d')}] {news['title']}\n"
                except: news_titles = "無相關新聞"
                
                results.append({"代號": ticker.replace('.TW', '').replace('.TWO', ''), "名稱": name, "最新收盤價": f"{close:.2f}", "特徵摘要": detail_note, "符合策略": selected_strategy, "新聞輿情": news_titles or "無", "原始代號": ticker})
        except Exception: pass
        time.sleep(0.3)
    return results

# --- 執行按鈕 ---
if st.button("🚀 開始全自動掃描 (雲端快取版)"):
    if not tickers_to_scan:
        st.warning("請先輸入股票代碼！")
    else:
        with st.spinner("系統極速運算中..."):
            st.session_state.scan_results = run_scan(tickers_to_scan, strategy)
            st.success("✅ 掃描任務完成！")
            st.balloons()
            gc.collect()

# --- 顯示結果與 AI 分析 ---
if st.session_state.get('scan_results') is not None:
    matched_stocks = st.session_state.scan_results
    if matched_stocks:
        st.write(f"### 🏆 符合【{strategy}】標的清單")
        res_df = pd.DataFrame(matched_stocks)
        st.dataframe(res_df.drop(columns=['新聞輿情', '原始代號'], errors='ignore'), use_container_width=True)
        
        # 繪圖區
        st.write("---")
        st.write("### 📈 個股技術線型 (互動圖表)")
        chart_options = {f"{s['代號']} {s['名稱']}": s['原始代號'] for s in matched_stocks}
        selected_label = st.selectbox("🔍 選擇標的查看詳細線圖：", list(chart_options.keys()))

        if selected_label:
            target_ticker = chart_options[selected_label]
            tk_chart = yf.Ticker(target_ticker)
            df_chart = tk_chart.history(period="6mo") # 畫圖才抓半年
            if not df_chart.empty:
                df_chart['SMA20'] = df_chart['Close'].rolling(20).mean()
                df_chart['STD20'] = df_chart['Close'].rolling(20).std()
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], increasing_line_color='#ef5350', decreasing_line_color='#26a69a', name='K線'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA20'], line=dict(color='blue', width=1.5), name='20MA (月線)'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA20'] + (df_chart['STD20'] * 2), line=dict(color='rgba(173,216,230,0.8)', dash='dot'), name='布林上軌'))
                fig.update_layout(title=f"【{selected_label}】 近半年走勢圖", xaxis_rangeslider_visible=False, height=450, template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

        # AI 區
      try:
                        stock_summary = "".join([f"■ 【{s['代號']} {s['名稱']}】 收盤價: {s['最新收盤價']} | 特徵: {s.get('特徵摘要', '')}\n近期新聞：\n{s.get('新聞輿情', '無')}\n\n" for s in matched_stocks])
                        prompt = f"策略：{strategy}\n日期：{datetime.now().strftime('%Y/%m/%d')}\n標的與新聞：\n{stock_summary}\n請分析：1.族群效應 2.突破真偽(搭配新聞) 3.停損建議"
                        genai.configure(api_key=api_key)
                        
                        # ---------------------------------------------------------
                        # 🌟 新增：終極雙重保險，自動降級機制
                        # ---------------------------------------------------------
                        try:
                            # 優先嘗試 1.5 世代模型
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            res = model.generate_content(prompt)
                            st.info("_(API 使用模型: `gemini-1.5-flash`)_")
                        except Exception:
                            try:
                                # 萬一失敗，降級使用最傳統、保證不斷線的基礎版
                                model = genai.GenerativeModel('gemini-pro')
                                res = model.generate_content(prompt)
                                st.info("_(API 使用模型: `gemini-pro`)_")
                            except Exception as e_inner:
                                st.error(f"雙重模型皆呼叫失敗，請檢查 API Key 是否有效。錯誤細節: {e_inner}")
                                res = None
                        
                        if res:
                            st.markdown(res.text)
                    except Exception as err: 
                        st.error(f"API 系統錯誤：{err}")
