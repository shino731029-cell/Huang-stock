import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="視覺化資產管理", layout="wide")
st.title("💼 專業級視覺化資產管理與 AI 健檢")

# 1. 建立或讀取持股資料
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = pd.DataFrame({
        "股票代號": ["2330.TW", "2317.TW", "2454.TW", "0050.TW", "2603.TW"],
        "買進均價": [800.0, 150.0, 1000.0, 140.0, 180.0],
        "持有股數": [1000, 2000, 1000, 5000, 2000],
        "停損設定價": [750.0, 140.0, 950.0, 135.0, 170.0]
    })

st.write("### 📝 編輯持股與停損清單")
edited_df = st.data_editor(
    st.session_state.portfolio,
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "買進均價": st.column_config.NumberColumn(format="%.2f"),
        "持有股數": st.column_config.NumberColumn(step=1),
        "停損設定價": st.column_config.NumberColumn(format="%.2f")
    }
)
st.session_state.portfolio = edited_df

st.write("---")

# 🌟 取消 st.rerun()，讓程式碼順暢地自然往下執行，避開版本衝突
if st.button("🔄 啟動視覺化資產結算", type="primary"):
    if not edited_df.empty:
        with st.spinner("正在抓取最新報價與繪製專業圖表..."):
            results = []
            total_cost = 0
            total_value = 0
            breached_alerts = [] 
            
            for index, row in edited_df.iterrows():
                ticker = str(row["股票代號"]).strip()
                if not ticker: continue
                
                try:
                    cost_price = float(row["買進均價"])
                    shares = int(row["持有股數"])
                    stop_price = float(row.get("停損設定價", 0.0))
                except ValueError:
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
                        
                        is_breached = (current_price < stop_price) and (stop_price > 0)
                        status_msg = "🚨 跌破停損" if is_breached else "✅ 安全"
                        
                        if is_breached:
                            breached_alerts.append(f"{name} ({ticker}) 現價 {current_price:.2f} 已跌破設定價 {stop_price:.2f}！")
                        
                        results.append({
                            "股票名稱": str(name), # 強制轉字串防呆
                            "代號": ticker,
                            "最新股價": current_price,
                            "買進均價": cost_price,
                            "持有股數": shares,
                            "投資成本": cost_total,
                            "目前市值": value_total,
                            "未實現損益": profit,
                            "報酬率 (%)": profit_pct,
                            "停損設定價": stop_price,
                            "狀態警報": status_msg
                        })
                except Exception as e:
                    pass

            if results:
                st.session_state.port_results = results
                st.session_state.total_cost = total_cost
                st.session_state.total_value = total_value
                st.session_state.breached_alerts = breached_alerts

# ==========================================
# 📊 顯示結果與視覺化圖表區
# ==========================================
if st.session_state.get('port_results'):
    results = st.session_state.port_results
    total_cost = st.session_state.total_cost
    total_value = st.session_state.total_value
    breached_alerts = st.session_state.breached_alerts
    
    res_df = pd.DataFrame(results)
    
    # 警報區
    if breached_alerts:
        st.error("### ⚠️ 風險警告：以下標的已觸及停損！")
        for alert in breached_alerts:
            st.write(f"- {alert}")
    else:
        st.success("🎉 目前所有持股皆在停損價之上，資產處於安全狀態。")
    
    # 總計區
    total_profit = total_value - total_cost
    total_profit_pct = (total_profit / total_cost) * 100 if total_cost > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("總投資成本 (TWD)", f"{total_cost:,.0f}")
    col2.metric("目前總市值 (TWD)", f"{total_value:,.0f}")
    col3.metric("總未實現損益", f"{total_profit:,.0f}", f"{total_profit_pct:.2f}%", delta_color="inverse")
    
    # ==========================================
    # 🚀 強大視覺化圖表區 (Treemap & Waterfall)
    # ==========================================
    st.write("---")
    st.write("### 📊 專業級視覺化資產分析")
    tab1, tab2 = st.tabs(["🔥 資產熱力圖 (Treemap)", "🌊 損益貢獻瀑布圖 (Waterfall)"])
    
    with tab1:
        st.caption("方塊大小代表「市值權重」，顏色代表「報酬率」(紅色獲利、綠色虧損)。")
        
        # 🌟 除蟲 1：過濾掉市值為 0 的標的，避免 Plotly 崩潰
        df_tree = res_df[res_df['目前市值'] > 0].copy()
        
        if not df_tree.empty:
            # 🌟 除蟲 2：用實體欄位取代 px.Constant，100% 相容所有 Plotly 版本
            df_tree['全部位'] = '我的投資組合'
            
            fig_tree = px.treemap(
                df_tree, 
                path=['全部位', '股票名稱'], 
                values='目前市值',
                color='報酬率 (%)', 
                color_continuous_scale='RdYlGn_r',
                color_continuous_midpoint=0,
                custom_data=['報酬率 (%)', '未實現損益']
            )
            fig_tree.update_traces(hovertemplate='<b>%{label}</b><br>市值: %{value:,.0f}<br>報酬率: %{customdata[0]:.2f}%<br>損益: %{customdata[1]:,.0f}')
            fig_tree.update_layout(height=550, margin=dict(t=30, l=10, r=10, b=10))
            st.plotly_chart(fig_tree, use_container_width=True)
        else:
            st.info("尚無大於零的部位可供繪製圖表。")
        
    with tab2:
        st.caption("瀑布圖展示每檔股票對「總損益」的具體貢獻。")
        names = res_df['股票名稱'].tolist() + ["總淨損益"]
        profits = res_df['未實現損益'].tolist() + [total_profit]
        measures = ["relative"] * len(res_df) + ["total"]
        
        fig_water = go.Figure(go.Waterfall(
            name="損益", orientation="v",
            measure=measures,
            x=names,
            textposition="outside",
            text=[f"{p:,.0f}" for p in profits],
            y=profits,
            connector={"line":{"color":"rgb(63, 63, 63)"}},
            decreasing={"marker":{"color":"#26a69a"}}, # 綠跌
            increasing={"marker":{"color":"#ef5350"}}, # 紅漲
            totals={"marker":{"color":"#1976d2"}}      # 總計藍色
        ))
        fig_water.update_layout(height=550, margin=dict(t=30, l=10, r=10, b=10))
        st.plotly_chart(fig_water, use_container_width=True)

    # ==========================================
    # 🤖 AI 投資組合健檢
    # ==========================================
    st.write("---")
    st.write("### 🤖 Gemini AI 持股與風險健檢")
    api_key = st.text_input("🔑 輸入 Gemini API Key 進行持股健檢", type="password")
    
    if st.button("✨ 產生專屬資產再平衡建議"):
        if api_key:
            with st.spinner("AI 首席財務官正在分析您的資產配置..."):
                try:
                    portfolio_summary = "\n".join([f"- {r['股票名稱']}({r['代號']}): 市值 {r['目前市值']:,.0f} (佔比 {r['目前市值']/total_value*100:.1f}%), 報酬率 {r['報酬率 (%)']:.2f}%, 狀態: {r['狀態警報']}" for r in results])
                    
                    prompt = f"""
                    【角色】：頂級機構基金經理人與風險控管專家
                    【當前日期】：{datetime.now().strftime('%Y/%m/%d')}
                    【我的投資組合明細】：
                    {portfolio_summary}
                    總市值: {total_value:,.0f}
                    總未實現損益: {total_profit:,.0f} ({total_profit_pct:.2f}%)
                    
                    請提供 3 段式專業建議：
                    1. **過度集中風險警告**：這組持股是否過度集中在特定產業或單一個股權重過大？
                    2. **汰弱留強指示**：依據報酬率與停損狀態，哪幾檔應該果斷砍掉？哪幾檔應該抱緊？
                    3. **下一步再平衡行動 (Rebalance)**：若要將資金轉向目前低基期或未來具潛力的板塊，您建議如何調整？
                    """
                    
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
                        st.error("❌ AI 呼叫失敗。請確認您的 API Key 權限。")
                except Exception as err:
                    st.error(f"系統錯誤：{err}")
        else:
            st.warning("⚠️ 請輸入 API Key！")
