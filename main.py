import os
import requests
import threading
import time
from flask import Flask, request

app = Flask(__name__)

# 🔐 Variáveis de ambiente
TOKEN = os.getenv("TOKEN")
BOT_ID = os.getenv("BOT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# 🧠 Estado global
last_welcome_message = {}  # {chat_id: message_id}
pending_users = {}         # {user_id: {"chat_id": ..., "message_id": ...}}

# 🎯 Gatilhos de compra
TRIGGERS = ["como comprar", "onde comprar", "quero comprar", "comprar rhap", "como compra"]

# --- FUNÇÕES AUXILIARES ---
def remove_user_if_pending(chat_id, user_id, message_id):
    """Apaga mensagem de captcha e expulsa usuário após 40s"""
    time.sleep(40)
    if user_id in pending_users:
        try:
            # Apagar mensagem do captcha
            requests.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": message_id
            })
            # Ban + unban (expulsão limpa)
            requests.post(f"{TELEGRAM_API}/banChatMember", json={
                "chat_id": chat_id,
                "user_id": user_id
            })
            time.sleep(0.3)
            requests.post(f"{TELEGRAM_API}/unbanChatMember", json={
                "chat_id": chat_id,
                "user_id": user_id
            })
        except Exception as e:
            print(f"[ERROR] Expulsão falhou: {e}")
        pending_users.pop(user_id, None)

def send_captcha(chat_id, user_id, first_name):
    """Envia mensagem de captcha com botão inline"""
    message = f"👋 Olá, {first_name}! Para confirmar que você é humano, clique no botão abaixo:"
    keyboard = {
        "inline_keyboard": [[{
            "text": "✅ Sou humano",
            "callback_data": f"captcha_{user_id}"
        }]]
    }
    payload = {
        "chat_id": chat_id,
        "text": message,
        "reply_markup": keyboard
    }
    response = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)
    
    if response.status_code == 200:
        msg_data = response.json()
        if msg_data.get("ok"):
            msg_id = msg_data["result"]["message_id"]
            pending_users[user_id] = {"chat_id": chat_id, "message_id": msg_id}
            thread = threading.Thread(target=remove_user_if_pending, args=(chat_id, user_id, msg_id))
            thread.daemon = True
            thread.start()

def send_welcome(chat_id, first_name):
    """Envia boas-vindas com menu inline"""
    global last_welcome_message

    # Apaga mensagem anterior (se houver)
    if chat_id in last_welcome_message:
        try:
            requests.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": last_welcome_message[chat_id]
            })
        except Exception as e:
            print(f"[WARN] Não apagou mensagem anterior: {e}")

    welcome_text = (
        f"🎮 Bem-vindo, {first_name}, à Comunidade Rhapsody!\n\n"
        "Este é o espaço oficial para quem acredita no poder da gamificação e das novas formas de engajar pessoas.\n\n"
        "Aqui você vai:\n"
        "✅ Descobrir novidades do projeto e do token RHAP\n"
        "✅ Entender como funciona nosso ecossistema de recompensas\n"
        "✅ Participar de eventos, ativações e conversas sobre o futuro digital\n"
        "✅ Conectar-se com outras pessoas que estão construindo junto\n\n"
        "🚀 Rhapsody Protocol — A nova camada do engajamento digital.\n\n"
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "🌐 Site oficial", "url": "https://rhapsodycoin.com/"}],
            [
                {"text": "📌 FAQ", "callback_data": "faq"},
                {"text": "🛒 Compre RHAP", "url": "https://rhapsody.criptocash.app/"}
            ],
            [{"text": "📱 Redes sociais", "callback_data": "redes_sociais"}]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": welcome_text,
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
        "disable_web_page_preview": True
    }

    response = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)
    if response.status_code == 200:
        msg_data = response.json()
        if msg_data.get("ok"):
            last_welcome_message[chat_id] = msg_data["result"]["message_id"]

def send_faq(chat_id):
    faq_text = (
        "📌 *Perguntas Frequentes – Rhapsody Protocol*\n\n"
        "*O que é o Rhapsody Protocol?*\n"
        "O Rhapsody Protocol é uma infraestrutura de gamificação para empresas, construída na blockchain Ethereum. Transformamos participação em valor real: marcas e criadores podem criar programas de engajamento com missões, níveis, conquistas e recompensas tokenizadas — com experiência Web2 e tecnologia Web3.\n\n"
        "*Para que serve o token $RHAP?*\n"
        "O $RHAP é o token utilitário do ecossistema. Ele será usado para recompensar usuários ativos, acessar benefícios exclusivos, participar de staking e gacha no MusicPlayce, mintar NFTs com utilidade e, futuramente, governar a DAO.\n\n"
        "*Quando será o lançamento do $RHAP?*\n"
        "O lançamento público do token $RHAP está previsto para *meados de junho de 2026*, aguardando confirmação final da data pela equipe e parceiros estratégicos.\n\n"
        "*Onde posso comprar $RHAP?*\n"
        "Atualmente, o $RHAP está em pré-venda exclusiva em [rhapsody.criptocash.app](https://rhapsody.criptocash.app). Após o lançamento, estará listado na Brasil Bitcoin.\n\n"
        "*Em qual blockchain o Rhapsody opera?*\n"
        "Na rede Ethereum (padrão ERC-20), garantindo segurança e interoperabilidade.\n\n"
        "*O Rhapsody é só mais um token especulativo?*\n"
        "Não. O Rhapsody nasce com utilidade real desde o dia 1, integrado à MusicPlayce (maior comunidade de músicos da América Latina) e com soluções B2B prontas para empresas de verdade."
    )

    keyboard = {
        "inline_keyboard": [
            [{"text": "📘 Leia nosso Whitepaper", "url": "https://rhapsody-coin.gitbook.io/rhapsody-protocol/"}]
        ]
    }

    payload = {
        "chat_id": chat_id,
        "text": faq_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": keyboard
    }
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def send_social_media(chat_id):
    payload = {
        "chat_id": chat_id,
        "text": "📱 *Redes Sociais*:\n\n"
                "📸 [Instagram](https://instagram.com/rhapsodycoin)\n"
                "🔗 [Twitter/X](https://twitter.com/rhapsodycoin)\n"
                "💼 [LinkedIn](https://linkedin.com/company/rhapsody-coin)\n"
                "💬 [Telegram Oficial](https://t.me/rhapsodycoin)",
        "parse_mode": "Markdown"
    }
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

# --- WEBHOOK PRINCIPAL ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return "OK"

        # === 1. TRATAR ENTRADA DE USUÁRIO (chat_member) ===
        if "chat_member" in data:
            chat_member = data["chat_member"]
            old_status = chat_member.get("old_chat_member", {}).get("status")
            new_status = chat_member.get("new_chat_member", {}).get("status")
            user = chat_member["new_chat_member"]["user"]
            chat_id = chat_member["chat"]["id"]

            # Só dispara se alguém entrou (de left/kicked → member)
            if old_status in ("left", "kicked") and new_status == "member":
                user_id = user["id"]
                if str(user_id) == BOT_ID:
                    return "OK"
                first_name = user.get("first_name", "amigo")
                send_captcha(chat_id, user_id, first_name)
            return "OK"

        # === 2. MENSAGENS DE TEXTO ===
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["
