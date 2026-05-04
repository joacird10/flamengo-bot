import requests
from datetime import datetime, timedelta
import os
import threading
from flask import Flask
import time

# =========================
# CONFIGURAÇÕES
# =========================
API_KEY = os.getenv("API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TEAM_ID = 127  # Flamengo

HEADERS = {
    "x-apisports-key": API_KEY
}

# CONTROLE
notificacao_enviada = False
placar_anterior = {}
ultimo_dia = None

# =========================
def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": msg
    })
    print("Telegram:", response.text)

# =========================
def converter_horario(data_api):
    dt = datetime.fromisoformat(data_api.replace("Z", ""))
    dt_br = dt - timedelta(hours=3)
    return dt_br.strftime("%H:%M")

# =========================
def buscar_jogo_hoje():
    hoje = datetime.now().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?team={TEAM_ID}&date={hoje}"

    response = requests.get(url, headers=HEADERS).json()
    jogos = response.get("response", [])

    if jogos:
        jogo = jogos[0]
        adversario = jogo["teams"]["away"]["name"]
        horario = converter_horario(jogo["fixture"]["date"])
        return True, adversario, horario

    return False, None, None

# =========================
def notificar_jogo_dia():
    global notificacao_enviada, ultimo_dia

    hoje = datetime.now().date()
    agora = datetime.now().strftime("%H:%M")

    if ultimo_dia != hoje:
        notificacao_enviada = False
        ultimo_dia = hoje

    if "09:00" <= agora <= "09:05" and not notificacao_enviada:
        tem_jogo, adversario, horario = buscar_jogo_hoje()

        if tem_jogo:
            enviar_telegram(f"📅 Hoje tem Flamengo x {adversario} às {horario}")

        notificacao_enviada = True

# =========================
def monitorar_gols():
    global placar_anterior

    url = f"https://v3.football.api-sports.io/fixtures?team={TEAM_ID}&live=all"
    response = requests.get(url, headers=HEADERS).json()

    for jogo in response.get("response", []):
        fixture_id = jogo["fixture"]["id"]

        time_casa = jogo["teams"]["home"]["name"]
        time_fora = jogo["teams"]["away"]["name"]

        gols_casa = jogo["goals"]["home"]
        gols_fora = jogo["goals"]["away"]

        atual = (gols_casa, gols_fora)

        if fixture_id not in placar_anterior:
            placar_anterior[fixture_id] = atual
            continue

        anterior = placar_anterior[fixture_id]

        if "Flamengo" in time_casa:
            if gols_casa > anterior[0]:
                enviar_telegram(f"⚽ GOOOL do Flamengo! {gols_casa} x {gols_fora}")

        if "Flamengo" in time_fora:
            if gols_fora > anterior[1]:
                enviar_telegram(f"⚽ GOOOL do Flamengo! {gols_casa} x {gols_fora}")

        placar_anterior[fixture_id] = atual

# =========================
def main():
    while True:
        try:
            print("Executando loop...")

            notificar_jogo_dia()
            monitorar_gols()

            time.sleep(300)  # 5 minutos

        except Exception as e:
            print("Erro:", e)
            time.sleep(60)

# =========================
# FLASK (necessário para Render)
# =========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot rodando"

def start_bot():
    main()

def start_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# =========================
if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    start_server()