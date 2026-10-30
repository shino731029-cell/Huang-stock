import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="我的投資組合", layout="wide")
st.title("💼 我的投資組合 (Portfolio)")

# 1. 建立或讀取持股資料
if 'portfolio' not in st.session_state:
    # 預設範例資料，你可以自己在網頁上手動刪除或修改
    st.session_state.portfolio = pd.DataFrame({
        "股票代號": ["2330.TW", "2317.TW", "0050.TW"],
        "買進均價": [800.0, 150.0, 140.0],
        "持有股數": [1000, 2000, 5000]
    })

st.write("### 📝 編輯持股清單")
st.caption("請在下方表格直接點擊修改代號、成本與股數。修改後系統會自動更新損益。")

# 使用 st.data_editor 讓使用者可以直接在網頁上編輯表格
edited_df = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic", # 允許使用者新增或刪除列
    use_container_width=True,
    column_config={
        "買進均價": st.column_config.NumberColumn(format="%.2f"),
        "持有股數": st.column_config.NumberColumn(step=1)
    }
)
st.session_state.portfolio = edited_df

st.write("---")
st.write("### 📈 即時損益與資產配置")

if st.button("🔄 計算最新損益"):
    if not edited_df.empty:
        with st.spinner("正在抓取最新報價..."):
            results = []
            total_cost = 0
            total_value = 0
            
            for index, row in edited_df.iterrows():
                ticker = str(row["股票代號"]).strip()
                cost_price = float(row["買進均價"])
                shares = int(row["持有股數"])
                
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
                        
                        results.append({
                            "股票名稱": name,
                            "代號": ticker,
                            "最新股價": f"{current_price:.2f}",
                            "買進均價": f"{cost_price:.2f}",
                            "持有股數": shares,
                            "投資成本": f"{cost_total:,.0f}",
                            "目前市值": f"{value_total:,.0f}",
                            "未實現損益": round(profit, 0),
                            "報酬率 (%)": round(profit_pct, 2)
                        })
                except Exception as e:
                    st.error(f"無法抓取 {ticker} 的資料。")

            if results:
                res_df = pd.DataFrame(results)
                
                # 顯示總計數據
                total_profit = total_value - total_cost
                total_profit_pct = (total_profit / total_cost) * 100 if total_cost > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("總投資成本 (TWD)", f"{total_cost:,.0f}")
                col2.metric("目前總市值 (TWD)", f"{total_value:,.0f}")
                col3.metric("總未實現損益", f"{total_profit:,.0f}", f"{total_profit_pct:.2f}%", delta_color="inverse")
                
                # 顯示明細表格 (套用紅綠顏色)
                def color_profit(val):
                    if pd.isna(val): return ''
                    if val > 0: return 'color: #ef5350' # 紅漲
                    elif val < 0: return 'color: #26a69a' # 綠跌
                    return ''
                    
                styled_df = res_df.style.applymap(color_profit, subset=['未實現損益', '報酬率 (%)'])
                st.dataframe(styled_df, use_container_width=True)

                # 畫出資產配置圓餅圖
                fig = go.Figure(data=[go.Pie(
                    labels=res_df['股票名稱'], 
                    values=res_df['目前市值'].str.replace(',', '').astype(float),
                    hole=.4,
                    textinfo='label+percent'
                )])
                fig.update_layout(title="資金配置比例 (依市值)", height=450)
                st.plotly_chart(fig, use_container_width=True)
                
    else:
        st.info("請先在上方表格輸入持股資料。")
