"""
send_brief.py
=============
Standalone script for 9:15 AM IST daily Telegram + WhatsApp briefing.
Add to crontab:
    45 3 * * 1-5 cd /path/to/dashboard && python send_brief.py

Env vars needed:
    TELEGRAM_BOT_TOKEN
    TELEGRAM_CHAT_ID
    TWILIO_SID          (optional, for WhatsApp)
    TWILIO_TOKEN
    WHATSAPP_NUMBER     (optional)
"""

import os, requests
from datetime import datetime

TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN","")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID","")
TWILIO_SID   = os.getenv("TWILIO_SID","")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN","")
WA_NUMBER    = os.getenv("WHATSAPP_NUMBER","")

TOP_PICKS = [
    ("BEL",    "Bharat Electronics", "₹420–435", "₹400", "₹530", 8.7),
    ("NESTLEIND","Nestlé India",     "₹1380–1410","₹1330","₹1600",8.4),
    ("ICICIBANK","ICICI Bank",       "₹1290–1330","₹1220","₹1700",8.2),
    ("BAJFINANCE","Bajaj Finance",   "₹8400–8700","₹7850","₹14000",8.0),
    ("LT",     "L&T",               "₹3300–3400","₹3100","₹4400",7.9),
]

def build_message():
    now=datetime.now().strftime("%d %b %Y")
    lines=[
        f"<b>🌅 India Invest v6.0 — Morning Brief {now}</b>\n",
        "<b>📊 Market Snapshot</b>",
        "• Gift Nifty: +0.4% → Positive open expected",
        "• VIX: 16.4 | PCR: 0.61 | Repo: 5.25% (Hold)",
        "• Crude: $91.4 | INR: ₹94.1/$\n",
        "<b>🏆 Today's Top 5 Picks</b>",
    ]
    for sym,name,entry,sl,t2,conf in TOP_PICKS:
        lines.append(f"• <b>{sym}</b> ({name})")
        lines.append(f"  Entry: {entry} | SL: {sl} | T2: {t2} | Conf: {conf}/10")
    lines += [
        "\n<b>⛔ Avoid Today</b>",
        "• IT sector (INFY, HCLTECH) — weak guidance",
        "• F&O ban: YESBANK, RBLBANK, PNB",
        "\n<b>📅 Results This Week</b>",
        "• Bajaj Finance (5 May) | M&M (6 May)",
        "\n<i>⚠️ Not SEBI advice. Always use stop losses.</i>",
    ]
    return "\n".join(lines)

def send_telegram(msg):
    if not TOKEN or not CHAT_ID:
        print("Telegram: missing credentials"); return False
    try:
        r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"},timeout=10)
        if r.status_code==200:
            print("Telegram: sent OK"); return True
        print(f"Telegram: failed {r.status_code}"); return False
    except Exception as e:
        print(f"Telegram error: {e}"); return False

def send_whatsapp(msg):
    if not all([TWILIO_SID,TWILIO_TOKEN,WA_NUMBER]):
        print("WhatsApp: missing credentials"); return False
    try:
        from twilio.rest import Client
        c=Client(TWILIO_SID,TWILIO_TOKEN)
        stripped=msg.replace("<b>","*").replace("</b>","*").replace("<i>","_").replace("</i>","_")
        stripped="".join(l for l in stripped if "<" not in l or ">" not in l)
        c.messages.create(from_="whatsapp:+14155238886",body=stripped,to=f"whatsapp:{WA_NUMBER}")
        print("WhatsApp: sent OK"); return True
    except Exception as e:
        print(f"WhatsApp error: {e}"); return False

if __name__=="__main__":
    now=datetime.now()
    print(f"[{now.strftime('%Y-%m-%d %H:%M')}] Running India Invest morning brief...")
    msg=build_message()
    send_telegram(msg)
    send_whatsapp(msg)
    print("Done.")
