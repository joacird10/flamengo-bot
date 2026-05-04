import requests
import json
import os
import time
from datetime import datetime, timedelta

# =========================
# CONFIG (ENV + FALLBACK)
# =========================
API_KEY = os.getenv("API_KEY", "37d43ab1701eba2466a068300d7d10a8")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8282685404:AAEGag9Dt_Z6Ttmko5l2spBY-7vJcqyYMzI")
CHAT_ID = os.getenv("CHAT_ID", "879871444")
TEAM_ID = 127

HEADERS = {"x-apisports-key": API_KEY}
STATE_FILE = "state.json"

# =========================
# STATE
# =========================
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

state = load_state()

# =========================
def enviar_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    response = requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    print("Telegram:", response.text)

# =========================
def converter_horario(data_api):
    dt = datetime.fromisoformat(data_api.replace("Z", ""))
    return (dt - timedelta(hours=3)).strftime("%H:%M")

# =========================
def buscar_jogo_hoje():
    hoje = datetime.now().strftime("%Y-%m-%d")
    url = f"https://v3.football.api-sports.io/fixtures?team={TEAM_ID}&date={hoje}"

    resp = requests.get(url, headers=HEADERS).json()
    jogos = resp.get("response", [])

    if not jogos:
        return None

    jogo = jogos[0]

    return {
        "fixture_id": jogo["fixture"]["id"],
        "adversario": jogo["teams"]["away"]["name"],
        "data": jogo["fixture"]["date"]
    }

# =========================
def notificar_9h():
    hoje = datetime.now().date()
    agora = datetime.now().strftime("%H:%M")

    if state.get("ultimo_dia") == str(hoje):
        return

    if "09:00" <= agora <= "09:05":

        jogo = buscar_jogo_hoje()

        if not jogo:
            print("Sem jogo hoje → parar")
            state.update({
                "ultimo_dia": str(hoje),
                "tem_jogo": False
            })
            save_state(state)
            return

        horario = converter_horario(jogo["data"])

        enviar_telegram(
            f"📅 Flamengo x {jogo['adversario']} às {horario}"
        )

        state.update({
            "ultimo_dia": str(hoje),
            "tem_jogo": True,
            "fixture_id": jogo["fixture_id"],
            "ultimo_placar": None,
            "jogo_finalizado": False,
            "jogo_iniciado": False
        })

        save_state(state)

# =========================
def monitorar_jogo():
    if not state.get("tem_jogo"):
        return

    if state.get("jogo_finalizado"):
        return

    fixture_id = state.get("fixture_id")

    url = f"https://v3.football.api-sports.io/fixtures?id={fixture_id}"
    resp = requests.get(url, headers=HEADERS).json()

    jogos = resp.get("response", [])
    if not jogos:
        return

    jogo = jogos[0]

    status = jogo["fixture"]["status"]["short"]
    gols_casa = jogo["goals"]["home"]
    gols_fora = jogo["goals"]["away"]

    atual = (gols_casa, gols_fora)
    anterior = state.get("ultimo_placar")

    print("Status:", status, "| Placar:", atual)

    # INÍCIO DO JOGO
    if status in ["1H", "2H"] and not state.get("jogo_iniciado"):
        enviar_telegram("▶️ Jogo do Flamengo começou!")
        state["jogo_iniciado"] = True

    # GOLS (sem duplicar)
    if anterior and atual != tuple(anterior):
        enviar_telegram(f"⚽ GOL! {gols_casa} x {gols_fora}")

    # FIM DO JOGO
    if status == "FT":
        enviar_telegram(f"🏁 Fim de jogo: {gols_casa} x {gols_fora}")
        state["jogo_finalizado"] = True

    state["ultimo_placar"] = atual
    save_state(state)

# =========================
def calcular_intervalo():
    if not state.get("tem_jogo"):
        return 3600  # 1h

    if state.get("jogo_finalizado"):
        return 3600

    if not state.get("jogo_iniciado"):
        return 900  # 15 min

    return 60  # jogo ao vivo

# =========================
def main():
    while True:
        try:
            print("\nExecutando loop...")

            notificar_9h()

            if state.get("tem_jogo"):
                monitorar_jogo()

            intervalo = calcular_intervalo()
            print(f"Próxima execução em {intervalo}s")

            time.sleep(intervalo)

        except Exception as e:
            print("Erro:", e)
            time.sleep(60)

# =========================
if __name__ == "__main__":
    main()
    
    
   from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

def start_bot():
    main()

def start_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    threading.Thread(target=start_bot).start()
    start_server()