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

UNIVERSE = {
    "DMLP": "CL=F",
    "BSM": "CL=F",
    "KRP": "CL=F",
    "VNOM": "CL=F",
    "TPL": "CL=F",
    "FNV": "GC=F",
    "WPM": "GC=F",
    "RGLD": "GC=F",
    "SAND": "GC=F",
}

# ---------- Correction clé ----------
def get_close_series(tk: str, period="1y"):
    df = yf.download(tk, period=period, auto_adjust=True, progress=False)
    if df is None or len(df) == 0:
        return None
    if isinstance(df, pd.DataFrame) and "Close" in df.columns:
        s = df["Close"]
    else:
        s = df.squeeze()
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return pd.Series(s).dropna()

def compute_metrics(ticker, proxy):
    try:
        px_t = get_close_series(ticker)
        px_p = get_close_series(proxy)
        if px_t is None or px_p is None:
            print(f"[{ticker}] pas de données téléchargées.")
            return None

        # Aligner les deux séries par date
        df = pd.concat([px_t, px_p], axis=1, keys=["t", "p"]).dropna()
        if len(df) < 60:
            print(f"[{ticker}] historique trop court ({len(df)} points)")
            return None

        rets = df.pct_change().dropna()
        corr = rets["t"].corr(rets["p"])
        beta = np.cov(rets["t"], rets["p"])[0, 1] / np.var(rets["p"])
        z = (df["t"].iloc[-1] - df["t"].mean()) / df["t"].std(ddof=0)
        return {"corr": float(corr), "beta": float(beta), "z": float(z), "price": float(df['t'].iloc[-1])}
    except Exception as e:
        print(f"[{ticker}] erreur: {e}")
        return None

def make_pdf(results):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M")
    pdf_path = os.path.join(OUTPUT_DIR, f"royalty_report_{now}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, 27*cm, f"Royalties Screener - Rapport du {now}")
    c.setFont("Helvetica", 10)
    y = 25*cm
    for t, v in results.items():
        line = f"{t} | Corr={v['corr']:.2f} | Beta={v['beta']:.2f} | Z={v['z']:.2f} | Prix={v['price']:.2f}"
        c.drawString(2*cm, y, line)
        y -= 0.5*cm
        if y < 2*cm:
            c.showPage()
            y = 27*cm
    c.save()
    return pdf_path
def send_email(pdf_path: str):
    host = os.getenv("SMTP_HOST", "").strip()             # ex: smtp-relay.brevo.com
    port = int(os.getenv("SMTP_PORT", "587"))             # 587 = TLS (STARTTLS), 465 = SSL
    user = os.getenv("SMTP_USER", "").strip()
    pwd  = os.getenv("SMTP_PASSWORD", "").strip()
    to   = os.getenv("TO_EMAIL", "").strip()
    from_addr = user or to

    if not all([host, port, user, pwd, to]):
        print("⚠️ Email non envoyé (variables SMTP manquantes)")
        return

    msg = EmailMessage()
    msg["Subject"] = "Daily Royalty Screener Report"
    msg["From"] = from_addr
    msg["To"] = to
    msg.set_content("Rapport quotidien en pièce jointe.")
    with open(pdf_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="pdf",
                           filename=os.path.basename(pdf_path))

    import smtplib, ssl, time
    ctx = ssl.create_default_context()

    try:
        if port == 465:
            # SSL direct
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as s:
                s.login(user, pwd)
                s.send_message(msg)
        else:
            # 587 (TLS/STARTTLS) ou 2525
            with smtplib.SMTP(host, port, timeout=20) as s:
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
                s.login(user, pwd)
                s.send_message(msg)
        print(f"📨 Email envoyé à {to}.")
    except Exception as e:
        print(f"❌ Envoi email échoué ({host}:{port}) : {e}")

if __name__ == "__main__":
    print("🚀 Lancement screener…")
    results = {}
    for t, p in UNIVERSE.items():
        print(f"Téléchargement {t} vs {p}…")
        m = compute_metrics(t, p)
        if m:
            results[t] = m
    if results:
        pdf = make_pdf(results)
        print(f"✅ PDF créé: {pdf}")
        send_email(pdf)
    else:
        print("Aucune donnée téléchargée ou erreur réseau.")
