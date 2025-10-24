import os
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import smtplib, ssl
from email.message import EmailMessage

# --- CONFIG ---
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- UNIVERSE ---
UNIVERSE = {
    "DMLP": "CL=F",   # Dorchester Minerals - pétrole
    "BSM": "CL=F",    # Black Stone Minerals
    "KRP": "CL=F",    # Kimbell Royalty
    "VNOM": "CL=F",   # Viper Energy
    "TPL": "CL=F",    # Texas Pacific Land
    "FNV": "GC=F",    # Franco-Nevada - or
    "WPM": "GC=F",    # Wheaton Precious
    "RGLD": "GC=F",   # Royal Gold
    "SAND": "GC=F",   # Sandstorm Gold
}

# --- FONCTIONS ---
def compute_metrics(ticker, proxy):
    try:
        df_t = yf.download(ticker, period="1y")["Close"]
        df_p = yf.download(proxy, period="1y")["Close"]
        if len(df_t) < 50 or len(df_p) < 50:
            return None
        corr = df_t.corr(df_p)
        beta = np.cov(df_t, df_p)[0][1] / np.var(df_p)
        z = (df_t.iloc[-1] - df_t.mean()) / df_t.std()
        return {"corr": corr, "beta": beta, "z": z}
    except Exception as e:
        print(f"Erreur {ticker}: {e}")
        return None

def make_pdf(results):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    pdf_path = os.path.join(OUTPUT_DIR, f"royalty_report_{now.replace(':','-')}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, 27 * cm, f"Royalty Screener Report - {now}")
    c.setFont("Helvetica", 10)
    y = 25 * cm
    for k, v in results.items():
        c.drawString(2 * cm, y, f"{k} | proxy={UNIVERSE[k]} | corr={v['corr']:.2f} | beta={v['beta']:.2f} | z={v['z']:.2f}")
        y -= 0.7 * cm
    c.save()
    return pdf_path

def send_email(pdf_path):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASSWORD")
    to_email  = os.getenv("TO_EMAIL")

    if not all([smtp_host, smtp_user, smtp_pass, to_email]):
        print("⚠️ Email non envoyé (variables SMTP manquantes)")
        return

    msg = EmailMessage()
    msg["Subject"] = "Daily Royalty Screener Report"
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.set_content("Voici le rapport PDF du screener royalties & commodities.")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf", filename=os.path.basename(pdf_path))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx) as server:
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
    print("📨 Email envoyé avec succès.")

# --- MAIN ---
if __name__ == "__main__":
    print("🚀 Démarrage du Royalty Screener...")
    results = {}
    for t, p in UNIVERSE.items():
        m = compute_metrics(t, p)
        if m:
            results[t] = m
    if results:
        pdf = make_pdf(results)
        print(f"✅ Rapport créé : {pdf}")
        send_email(pdf)
    else:
        print("Aucune donnée récupérée.")
