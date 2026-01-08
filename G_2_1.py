# -*- coding: utf-8 -*-
"""
Created on Thu Jan  8 08:59:15 2026

@author: chen_
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from datetime import timedelta
import yfinance as yf

# --- Page Configuration ---
st.set_page_config(page_title="黃金走勢分析", layout="wide")

# --- Matplotlib Font Fix ---
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False 

# --- Data Loading Logic ---
@st.cache_data # Cache data to prevent reloading on every click
def load_data():
    """讀取 CSV 資料"""
    path = 'GoldPassbook@202601071041.csv'
    # In Streamlit, we should handle the file not found error gracefully
    try:
        for enc in ['utf-8-sig', 'cp950', 'utf-8']:
            try:
                df = pd.read_csv(path, encoding=enc)
                df.columns = df.columns.str.strip() 
                df['日期'] = pd.to_datetime(df['日期'], format='%Y%m%d')
                return df.sort_values('日期')
            except Exception:
                continue
    except FileNotFoundError:
        st.error(f"找不到檔案: {path}")
    return None

def get_market_data(period_str):
    """獲取 Yahoo Finance 數據"""
    days_map = {"1個月": "30d", "3個月": "90d", "6個月": "180d", "1年": "1y", "2年": "2y"}
    yf_period = days_map.get(period_str, "1y")
    try:
        # Download data
        data = yf.download(["TWD=X", "GC=F"], period=yf_period, interval="1d", progress=False)
        if data.empty: return None
        
        # Calculate rates
        curr_rate = data['Close']['TWD=X'].iloc[-1]
        curr_gold_usd = data['Close']['GC=F'].iloc[-1]
        
        # Historical conversion (TWD/g)
        hist_gold_twd = (data['Close']['GC=F'] * data['Close']['TWD=X']) / 31.1035
        curr_gold_twd = (curr_gold_usd * curr_rate) / 31.1035
        
        return {
            "rate": curr_rate,
            "gold_usd": curr_gold_usd,
            "gold_twd_live": curr_gold_twd,
            "hist_gold_twd": hist_gold_twd,
            "yf_data": data
        }
    except:
        return None

# --- Main App Interface ---
st.title("💰 黃金走勢分析 Dashboard")

# 1. Sidebar Controls
with st.sidebar:
    st.header("設定")
    period_choice = st.selectbox(
        "分析時間軸", 
        ["1個月", "3個月", "6個月", "1年", "2年"],
        index=0
    )
    refresh_btn = st.button("同步更新數據")

# Load CSV Data
df_local = load_data()

if df_local is not None:
    # 2. Fetch Market Data
    market = get_market_data(period_choice)
    
    if market:
        # Filter Local Data based on period
        days_map = {"1個月": 30, "3個月": 90, "6個月": 180, "1年": 365, "2年": 730}
        cutoff = df_local['日期'].max() - timedelta(days=days_map[period_choice])
        local_subset = df_local[df_local['日期'] >= cutoff].copy()

        # 3. KPI Metrics (Data Dashboard)
        if not local_subset.empty:
            l_sell = local_subset['本行賣出價格'].iloc[-1]
            l_buy = local_subset['本行買入價格'].iloc[-1]
            sell_premium = l_sell - market['gold_twd_live']
            buy_discount = l_buy - market['gold_twd_live']

            col1, col2, col3 = st.columns(3)
            col1.metric("國際參考價 (TWD/g)", f"{market['gold_twd_live']:.1f}")
            col2.metric("本行賣出 (向行買)", f"{l_sell:,.1f}", f"{sell_premium:+.1f} 溢價")
            col3.metric("本行買入 (賣給行)", f"{l_buy:,.1f}", f"{buy_discount:+.1f} 折價")
            
            st.info(f"即時匯率: {market['rate']:.2f} | 國際金價: ${market['gold_usd']:.1f}/oz")
        
        # 4. Charts (2x2 Layout)
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # [1] Local Prices
        ax1 = axes[0, 0]
        if not local_subset.empty:
            ax1.plot(local_subset['日期'], local_subset['本行賣出價格'], color='#d32f2f', label="本行賣出")
            ax1.plot(local_subset['日期'], local_subset['本行買入價格'], color='#388e3c', label="本行買入")
            ax1.axhline(market['gold_twd_live'], color='blue', ls='--', alpha=0.5, label="國際現價")
            ax1.fill_between(local_subset['日期'], local_subset['本行買入價格'], local_subset['本行賣出價格'], color='gray', alpha=0.1)
        ax1.set_title("本地銀行報價走勢")
        ax1.legend(loc='upper left')

        # [2] Exchange Rate
        ax2 = axes[0, 1]
        ax2.plot(market['yf_data'].index, market['yf_data']['Close']['TWD=X'], color='purple')
        ax2.set_title("USD/TWD 匯率波動")

        # [3] USD Gold Price
        ax3 = axes[1, 0]
        ax3.plot(market['yf_data'].index, market['yf_data']['Close']['GC=F'], color='orange')
        ax3.set_title("國際金價 (USD/oz)")

        # [4] Premium/Discount
        ax4 = axes[1, 1]
        if not local_subset.empty:
            # Reindex/Merge logic for premium
            hist_intl = market['hist_gold_twd'].reset_index()
            hist_intl.columns = ['日期', 'intl']
            merged = pd.merge(local_subset[['日期', '本行賣出價格', '本行買入價格']], hist_intl, on='日期')
            
            ax4.plot(merged['日期'], merged['本行賣出價格'] - merged['intl'], color='#d32f2f', label="賣出溢價")
            ax4.plot(merged['日期'], merged['本行買入價格'] - merged['intl'], color='#388e3c', label="買入折價")
            ax4.axhline(0, color='black', lw=1)
            ax4.set_title("溢價/折價分析")
            ax4.legend(loc='upper left')

        # Cleanup labels
        for ax in axes.flatten():
            plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
        
        fig.tight_layout()
        st.pyplot(fig)

    else:
        st.error("無法連線至 Yahoo Finance，請檢查網路。")
else:
    st.warning("請確認 CSV 檔案路徑正確且編碼相符。")