print("✅ main.py lancé")
import os, sys
print("CWD:", os.getcwd())
print("Contenu racine:", os.listdir("."))
print("Contenu app/:", os.listdir("app") if os.path.exists("app") else "app/ absent")
