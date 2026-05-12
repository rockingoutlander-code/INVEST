"""
screener_webhook.py
====================
Runs every 30 minutes during market hours.
Scans 25 stocks for breakout conditions → sends Telegram alert.

Crontab (every 30 min, Mon-Fri, 9:15 AM – 3:30 PM IST = 3:45 AM – 10:00 AM UTC):
    */30 3-9 * * 1-5 cd /path/to/dashboard && python screener_webhook.py

Or run continuously with schedule:
    python screener_webhook.py --daemon
"""

import os, sys, time, requests
import pandas as pd
import numpy as np
from datetime import datetime

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")

UNIVERSE = [
    "BEL","NESTLEIND","HDFCBANK","ICICIBANK","HAL","BAJFINANCE",
    "APOLLOHOSP","BHARTIARTL","MM","LT","RELIANCE","HINDUNILVR",
    "TITAN","MARUTI","POWERGRID","DRREDDY","ITC","NTPC","COALINDIA",
    "JSWSTEEL","TATAMOTORS","ADANIPORTS","SUNPHARMA","SIEMENS","PRAJIND",
]

def fetch_data(sym, period="3mo"):
    try:
        r=requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}.NS",
            headers={"User-Agent":"Mozilla/5.0"},
            params={"range":period,"interval":"1d"},timeout=10)
        res=r.json()["chart"]["result"][0]
        q=res["indicators"]["quote"][0]
        df=pd.DataFrame({"Date":pd.to_datetime(res["timestamp"],unit="s"),
            "Open":q["open"],"High":q["high"],"Low":q["low"],
            "Close":q["close"],"Volume":q["volume"]}).dropna()
        return df
    except: return pd.DataFrame()

def compute_signals(df):
    if df.empty or len(df)<20: return {}
    c=df["Close"]; v=df["Volume"]
    s50=float(c.rolling(50).mean().iloc[-1]) if len(c)>=50 else None
    cmp=float(c.iloc[-1])
    d=c.diff(); g=d.clip(lower=0).rolling(14).mean(); l=(-d.clip(upper=0)).rolling(14).mean()
    rsi=float((100-100/(1+g/l.replace(0,.001))).iloc[-1])
    atr=float(((df["High"]-df["Low"]).rolling(14).mean()).iloc[-1])
    vr=float(v.iloc[-1]/v.rolling(20).mean().iloc[-1]) if len(v)>=20 else 1.0
    hi52=float(c.rolling(min(252,len(c))).max().iloc[-1])
    pct_from_hi=(cmp-hi52)/hi52*100
    return {
        "cmp":round(cmp,2),"rsi":round(rsi,1),
        "above50":cmp>s50 if s50 else False,
        "atr":round(atr,2),"vol_ratio":round(vr,2),
        "pct_from_hi":round(pct_from_hi,1),
        "hi52":round(hi52,2),
    }

def scan_all():
    alerts=[]
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning {len(UNIVERSE)} stocks...")
    for sym in UNIVERSE:
        df=fetch_data(sym,"6mo")
        t=compute_signals(df)
        if not t: continue
        reasons=[]
        if t["pct_from_hi"]>-3 and t["vol_ratio"]>1.4:
            reasons.append(f"Near 52W high ({t['pct_from_hi']:.1f}%) · Vol {t['vol_ratio']:.1f}x")
        if t["above50"] and 45<=t["rsi"]<=65 and t["vol_ratio"]>1.5:
            reasons.append(f"Above 50DMA · RSI {t['rsi']:.0f} · Strong volume")
        if t["rsi"]<32:
            reasons.append(f"RSI oversold {t['rsi']:.0f} — potential bounce")
        if reasons:
            alerts.append({"sym":sym,"cmp":t["cmp"],"reasons":reasons})
            print(f"  🚀 {sym}: {' | '.join(reasons)}")
    return alerts

def send_alerts(alerts):
    if not TOKEN or not CHAT_ID: return
    if not alerts:
        print("No alerts triggered."); return
    now=datetime.now().strftime("%I:%M %p IST")
    lines=[f"<b>⚡ Breakout Scanner — {now}</b>\n"]
    for a in alerts[:8]:
        lines.append(f"🟢 <b>{a['sym']}</b> @ ₹{a['cmp']}")
        for r in a["reasons"]:
            lines.append(f"   → {r}")
        lines.append("")
    lines.append("<i>Not SEBI advice. Use stop losses.</i>")
    msg="\n".join(lines)
    try:
        r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"},timeout=10)
        print(f"Telegram: {'OK' if r.status_code==200 else 'FAIL'} ({len(alerts)} alerts sent)")
    except Exception as e:
        print(f"Telegram error: {e}")

def is_market_hours():
    now=datetime.now()
    if now.weekday()>=5: return False
    t=now.hour*60+now.minute
    return 9*60+15 <= t <= 15*60+30

if __name__=="__main__":
    daemon="--daemon" in sys.argv
    if daemon:
        import schedule
        print("Starting scanner daemon (every 30 min during market hours)...")
        schedule.every(30).minutes.do(lambda: send_alerts(scan_all()) if is_market_hours() else None)
        while True:
            schedule.run_pending(); time.sleep(60)
    else:
        alerts=scan_all()
        send_alerts(alerts)
