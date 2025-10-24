print("### VER_MARK_1 ###")
import os, ssl, datetime
import pandas as pd
import numpy as np
import yfinance as yf
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import smtplib
from email.message import EmailMessage

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --- Univers de test ---
UNIVERSE = {
    "DMLP": "CL=F",
    "BSM": "CL=F",
    "KRP": "CL=F",
    "VNOM": "CL=F",
    "TPL":  "CL=F",
    "FNV":  "GC=F",
    "WPM":  "GC=F",
    "RGLD": "GC=F",
    "SAND": "GC=F"
}
def get_close_series(tk: str, period="1y"):
    df = yf.download(tk, period=period, auto_adjust=True, progress=False)
    if df is None or len(df) == 0:
        return None
    # Extraire une Series Close propre (même si yfinance renvoie parfois un DF)
    s = df["Close"] if "Close" in df.columns else df.squeeze()
    if isinstance(s, pd.DataFrame):
        # Certaines bourses renvoient 'Close' multi-colonnes -> on prend la 1ère
        s = s.iloc[:, 0]
    s = pd.Series(s).dropna()
    s.name = tk
    return s
def compute_metrics(ticker, proxy):
    try:
        px_t = get_close_series(ticker, period="1y")
        px_p = get_close_series(proxy,  period="1y")
        if px_t is None or px_p is None:
            print(f"[{ticker}] pas de données téléchargées.")
            return None

        # Aligner proprement
        rets_t = px_t.pct_change()
        rets_p = px_p.pct_change()
        aligned = pd.concat([rets_t, rets_p], axis=1, keys=["t","p"]).dropna()
        if len(aligned) < 60:
            return None

        corr = aligned["t"].corr(aligned["p"])
        beta = np.cov(aligned["t"], aligned["p"])[0, 1] / np.var(aligned["p"])
        z = (px_t.iloc[-1] - px_t.mean()) / px_t.std(ddof=0)

        return {
            "corr": float(corr),
            "beta": float(beta),
            "z": float(z),
            "price": float(px_t.iloc[-1])
        }
    except Exception as e:
        print(f"[{ticker}] erreur: {e}")
        return None
def make_pdf(results):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M")
    pdf_path = os.path.join(OUTPUT_DIR, f"royalty_report_{now}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, 27*cm, f"Royalties & Commodities — Rapport {now}")
    c.setFont("Helvetica", 10)
    y = 25*cm
    c.drawString(2*cm, y, "Ticker | Proxy | Corr(1y ret) | Beta | Z-score | Prix")
    y -= 0.5*cm
    for t, v in results.items():
        line = f"{t} | {UNIVERSE[t]} | {v['corr']:.2f} | {v['beta']:.2f} | {v['z']:.2f} | {v['price']:.2f}"
        c.drawString(2*cm, y, line)
        y -= 0.6*cm
        if y < 2.5*cm:
            c.showPage()
            y = 27*cm
    c.save()
    return pdf_path

def send_email(pdf_path):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "465"))
    user = os.getenv("SMTP_USER")
    pwd  = os.getenv("SMTP_PASSWORD")
    to   = os.getenv("TO_EMAIL")

    if not all([host, user, pwd, to]):
        print("⚠️ Email non envoyé (variables SMTP manquantes)")
        return

    msg = EmailMessage()
    msg["Subject"] = "Daily Royalty Screener Report"
    msg["From"] = user
    msg["To"] = to
    msg.set_content("Voici le rapport quotidien en pièce jointe.")

    with open(pdf_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(pdf_path)
        )

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx) as s:
        s.login(user, pwd)
        s.send_message(msg)
    print("📨 Email envoyé.")

if __name__ == "__main__":
    print("🚀 Lancement screener…")
    results = {}
    for t, p in UNIVERSE.items():
        print(f"Téléchargement {t} vs {p}...")
        m = compute_metrics(t, p)
        if m:
            results[t] = m
    if results:
        pdf = make_pdf(results)
        print(f"✅ PDF créé: {pdf}")
        send_email(pdf)
    else:
        print("Aucune donnée téléchargée ou erreur réseau.")
