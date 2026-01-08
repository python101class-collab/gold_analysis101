# -*- coding: utf-8 -*-
"""
Created on Thu Jan  8 04:52:17 2026

@author: chen_
"""

import pandas as pd
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import timedelta
import yfinance as yf

# --- 基礎設定 ---
plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei'] 
plt.rcParams['axes.unicode_minus'] = False 

def load_data():
    """讀取 CSV 資料"""
    path = 'GoldPassbook@202601071041.csv'
    for enc in ['utf-8-sig', 'cp950', 'utf-8']:
        try:
            df = pd.read_csv(path, encoding=enc)
            df.columns = df.columns.str.strip() 
            df['日期'] = pd.to_datetime(df['日期'], format='%Y%m%d')
            return df.sort_values('日期')
        except Exception:
            continue
    return None

class GoldApp:
    def __init__(self, root, df):
        self.df = df
        self.root = root
        self.root.title("黃金走勢分析")
        self.root.geometry("1400x1000") 
        
        self.root.rowconfigure(2, weight=1) 
        self.root.columnconfigure(0, weight=1)

        # 1. 控制面板
        header = tk.Frame(root, pady=10)
        header.grid(row=0, column=0, sticky="ew")
        
        tk.Label(header, text="分析時間軸:", font=("Microsoft JhengHei", 14)).pack(side=tk.LEFT, padx=5)
        self.period = ttk.Combobox(header, values=["1個月", "3個月", "6個月", "1年", "2年"], 
                                   font=("Microsoft JhengHei", 12), state="readonly", width=10)
        self.period.pack(side=tk.LEFT, padx=5)
        self.period.current(0)
        
        btn = tk.Button(header, text="同步更新所有數據", command=self.update_all, bg="#28a745", fg="white", 
                        font=("Microsoft JhengHei", 12, "bold"), padx=20)
        btn.pack(side=tk.LEFT, padx=15)

        # 2. 數據看板
        self.info = tk.Label(root, text="正在獲取數據...", font=("Microsoft JhengHei", 13), 
                             bg="#f1f3f5", relief="groove", pady=15, fg="#2c3e50", justify=tk.LEFT) 
        self.info.grid(row=1, column=0, sticky="ew", padx=30, pady=10)

        # 3. 2x2 圖表區
        self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8), dpi=100) 
        self.canvas = FigureCanvasTkAgg(self.fig, root)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.grid(row=2, column=0, sticky="nsew", padx=30, pady=10)

        self.update_all()

    def get_market_data(self, period_str):
        """獲取 Yahoo Finance 數據"""
        days_map = {"1個月": "30d", "3個月": "90d", "6個月": "180d", "1年": "1y", "2年": "2y"}
        yf_period = days_map.get(period_str, "1y")
        try:
            data = yf.download(["TWD=X", "GC=F"], period=yf_period, interval="1d", progress=False)
            if data.empty: return None, None, None, None, None
            
            curr_rate = data['Close']['TWD=X'].iloc[-1]
            curr_gold_usd = data['Close']['GC=F'].iloc[-1]
            
            # 歷史換算價 (TWD/g)
            hist_gold_twd = (data['Close']['GC=F'] * data['Close']['TWD=X']) / 31.1035
            curr_gold_twd = (curr_gold_usd * curr_rate) / 31.1035
            
            return curr_rate, curr_gold_usd, curr_gold_twd, hist_gold_twd, data
        except:
            return None, None, None, None, None

    def update_all(self):
        rate, gold_usd, gold_twd_live, hist_gold_twd, yf_data = self.get_market_data(self.period.get())
        
        if rate is None:
            messagebox.showerror("錯誤", "無法連線至 Yahoo Finance")
            return

        days_map = {"1個月": 30, "3個月": 90, "6個月": 180, "1年": 365, "2年": 730}
        cutoff = self.df['日期'].max() - timedelta(days=days_map[self.period.get()])
        local_data = self.df[self.df['日期'] >= cutoff].copy()

        # --- 數據顯示邏輯 ---
        if not local_data.empty:
            l_sell = local_data['本行賣出價格'].iloc[-1]
            l_buy = local_data['本行買入價格'].iloc[-1]
            sell_premium = l_sell - gold_twd_live  # 買進成本高於國際價多少
            buy_discount = l_buy - gold_twd_live   # 賣回銀行損失多少 (通常為負數)
            
            info_text = (
                f"【國際即時】匯率: {rate:.2f} | 金價: ${gold_usd:.1f}/oz | 國際參考價: {gold_twd_live:.1f} TWD/g\n"
                f"【本行報價】買入價(賣給銀行): {l_buy:,.1f} | 賣出價(向銀行買): {l_sell:,.1f}\n"
                f"【價差分析】賣出溢價: {sell_premium:+.1f} (高於國際) | 買入折價: {buy_discount:+.1f} (低於國際)"
            )
        else:
            info_text = "選取區間內無本地 CSV 資料"
        self.info.config(text=info_text)

        # --- 繪圖 ---
        for ax in self.axes.flatten(): ax.clear()

        # [1] 本地買賣價走勢 (左上)
        ax1 = self.axes[0, 0]
        if not local_data.empty:
            ax1.plot(local_data['日期'], local_data['本行賣出價格'], color='#d32f2f', label="本行賣出(最高)")
            ax1.plot(local_data['日期'], local_data['本行買入價格'], color='#388e3c', label="本行買入(最低)")
            ax1.axhline(gold_twd_live, color='blue', ls='--', alpha=0.5, label="國際現價")
            ax1.fill_between(local_data['日期'], local_data['本行買入價格'], local_data['本行賣出價格'], color='gray', alpha=0.1)
        ax1.set_title("本地銀行買/賣報價走勢")
        ax1.legend(fontsize=8)

        # [2] 匯率走勢 (右上)
        ax2 = self.axes[0, 1]
        ax2.plot(yf_data.index, yf_data['Close']['TWD=X'], color='purple')
        ax2.set_title("USD/TWD 匯率波動")
        ax2.grid(True, alpha=0.3)

        # [3] 國際金價走勢 (左下)
        ax3 = self.axes[1, 0]
        ax3.plot(yf_data.index, yf_data['Close']['GC=F'], color='orange')
        ax3.set_title("國際金價走勢 (USD/oz)")
        ax3.grid(True, alpha=0.3)

        # [4] 溢價/折價分析 (右下)
        ax4 = self.axes[1, 1]
        if not local_data.empty:
            # 對齊日期計算歷史溢價
            merged = pd.merge(local_data[['日期', '本行賣出價格', '本行買入價格']], 
                              hist_gold_twd.reset_index().rename(columns={'Date':'日期', 0:'intl'}), on='日期')
            ax4.plot(merged['日期'], merged['本行賣出價格'] - merged['intl'], color='#d32f2f', label="賣出溢價")
            ax4.plot(merged['日期'], merged['本行買入價格'] - merged['intl'], color='#388e3c', label="買入折價")
            ax4.axhline(0, color='black', lw=1, ls='-')
            ax4.set_title("與國際價之偏差 (溢價/折價)")
            ax4.legend(fontsize=8)
        
        for ax in self.axes.flatten():
            plt.setp(ax.get_xticklabels(), rotation=20, horizontalalignment='right', fontsize=8)

        self.fig.tight_layout()
        self.canvas.draw()

if __name__ == "__main__":
    data = load_data()
    if data is not None:
        root = tk.Tk()
        app = GoldApp(root, data)
        root.mainloop()