import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="我的投資組合", layout="wide")
st.title("💼 我的投資組合與風險控管")

# 1. 建立或讀取持股資料 (新增停損價欄位)
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame({
        "股票代號": ["2330.TW", "2317.TW", "0050.TW"],
        "買進均價": [800.0, 150.0, 140.0],
        "持有股數": [1000, 2000, 5000],
        "停損設定價": [750.0, 140.0, 135.0] # 🌟 新增：預設的停損價格
    })

st.write("### 📝 編輯持股與停損清單")
st.caption("請在下方表格輸入代號、成本、股數，並務必設定「停損設定價」。(若不想設定停損，可輸入 0)")

# 使用 st.data_editor 讓使用者可以直接在網頁上編輯表格
edited_df = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "買進均價": st.column_config.NumberColumn(format="%.2f"),
        "持有股數": st.column_config.NumberColumn(step=1),
        "停損設定價": st.column_config.NumberColumn(format="%.2f", help="當現價跌破此價格時，系統會發出紅色警報")
    }
)
st.session_state.portfolio = edited_df

st.write("---")
st.write("### 📈 即時損益與風險體檢")

if st.button("🔄 計算最新損益與檢查停損"):
    if not edited_df.empty:
        with st.spinner("正在抓取最新報價與比對停損條件..."):
            results = []
            total_cost = 0
            total_value = 0
            breached_alerts = [] # 紀錄跌破停損的股票
            
            for index, row in edited_df.iterrows():
                ticker = str(row["股票代號"]).strip()
                cost_price = float(row["買進均價"])
                shares = int(row["持有股數"])
                stop_price = float(row.get("停損設定價", 0.0))
                
                if not ticker:
                    continue
                    
                try:
                    tk = yf.Ticker(ticker)
                    hist = tk.history(period="1d")
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        name = tk.info.get('shortName', ticker)
                        
                        cost_total = cost_price * shares
                        value_total = current_price * shares
                        profit = value_total - cost_total
                        profit_pct = (profit / cost_total) * 100 if cost_total > 0 else 0
                        
                        total_cost += cost_total
                        total_value += value_total
                        
                        # 🌟 停損判斷邏輯
                        is_breached = (current_price < stop_price) and (stop_price > 0)
                        status_msg = "🚨 跌破停損" if is_breached else "✅ 安全"
                        
                        if is_breached:
                            breached_alerts.append(f"{name} ({ticker}) 現價 {current_price:.2f} 已跌破設定價 {stop_price:.2f}！")
                        
                        results.append({
                            "股票名稱": name,
                            "代號": ticker,
                            "最新股價": f"{current_price:.2f}",
                            "買進均價": f"{cost_price:.2f}",
                            "持有股數": shares,
                            "投資成本": f"{cost_total:,.0f}",
                            "目前市值": f"{value_total:,.0f}",
                            "未實現損益": round(profit, 0),
                            "報酬率 (%)": round(profit_pct, 2),
                            "停損設定價": f"{stop_price:.2f}",
                            "狀態警報": status_msg
                        })
                except Exception as e:
                    st.error(f"無法抓取 {ticker} 的資料。")

            if results:
                # 🌟 優先顯示大紅色的停損警告區塊
                if breached_alerts:
                    st.error("### ⚠️ 風險警告：請注意以下標的已觸及停損！")
                    for alert in breached_alerts:
                        st.write(f"- {alert}")
                    st.write("*(交易金律：截斷虧損，讓利潤奔跑。請審慎評估是否執行停損紀律)*")
                else:
                    st.success("🎉 目前所有持股皆在停損價之上，資產處於安全狀態。")
                
                res_df = pd.DataFrame(results)
                
                # 顯示總計數據
                total_profit = total_value - total_cost
                total_profit_pct = (total_profit / total_cost) * 100 if total_cost > 0 else 0
                
                col1, col2, col3 = st
