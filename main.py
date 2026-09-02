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

# 📄 Endereço do Contrato
CONTRACT_ADDRESS = "0xA77720b75609962d680D3456c2b2F85515f797da"

# 🧠 Estado global
last_welcome_message = {}
pending_users = {}

# 🎯 Gatilhos de compra
TRIGGERS = ["como comprar", "onde comprar", "quero comprar", "comprar rhap", "como compra"]

# --- FUNÇÕES AUXILIARES ---

def send_contract(chat_id, reply_to_message_id=None):
    contract_text = (
        "📄 **Contrato oficial do token $RHAP:**\n\n"
        f"`{CONTRACT_ADDRESS}`\n\n"
        "⚠️ *Sempre verifique se o endereço está correto antes de interagir!*"
    )
    payload = {
        "chat_id": chat_id,
        "text": contract_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if reply_to_message_id:
        payload["reply_to_message_id"] = reply_to_message_id
        
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def remove_user_if_pending(chat_id, user_id, message_id):
    time.sleep(40)
    if user_id in pending_users:
        try:
            requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
            requests.post(f"{TELEGRAM_API}/banChatMember", json={"chat_id": chat_id, "user_id": user_id})
            time.sleep(0.3)
            requests.post(f"{TELEGRAM_API}/unbanChatMember", json={"chat_id": chat_id, "user_id": user_id})
        except Exception as e:
            print(f"[ERROR] Expulsão falhou: {e}")
        pending_users.pop(user_id, None)

def send_captcha(chat_id, user_id, first_name):
    message = f"👋 Olá, {first_name}! Para confirmar que você é humano, clique no botão abaixo:"
    keyboard = {"inline_keyboard": [[{"text": "✅ Sou humano", "callback_data": f"captcha_{user_id}"}]]}
    payload = {"chat_id": chat_id, "text": message, "reply_markup": keyboard}
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
    global last_welcome_message
    if chat_id in last_welcome_message:
        try:
            requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": last_welcome_message[chat_id]})
        except Exception:
            pass

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
            [{"text": "📌 FAQ", "callback_data": "faq"}, {"text": "🛒 Compre RHAP", "url": "https://rhapsody.criptocash.app/"}],
            [{"text": "📱 Redes sociais", "callback_data": "redes_sociais"}]
        ]
    }

    payload = {"chat_id": chat_id, "text": welcome_text, "parse_mode": "Markdown", "reply_markup": keyboard, "disable_web_page_preview": True}
    response = requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)
    if response.status_code == 200:
        msg_data = response.json()
        if msg_data.get("ok"):
            last_welcome_message[chat_id] = msg_data["result"]["message_id"]

def send_faq(chat_id):
    faq_text = (
        "📌 *Perguntas Frequentes – Rhapsody Protocol*\n\n"
        "*O que é o Rhapsody Protocol?*\n"
        "O Rhapsody Protocol é uma infraestrutura de gamificação para empresas, construída na blockchain Ethereum. Transformamos participação em valor real.\n\n"
        "*Para que serve o token $RHAP?*\n"
        "O $RHAP é o token utilitário do ecossistema. Ele será usado para recompensar usuários ativos, acessar benefícios exclusivos e participar do ecossistema MusicPlayce.\n\n"
        "*Onde posso comprar $RHAP?*\n"
        "Atualmente, o $RHAP está em pré-venda exclusiva em [rhapsody.criptocash.app](https://rhapsody.criptocash.app).\n\n"
        "*Em qual blockchain o Rhapsody opera?*\n"
        "Na rede Ethereum (padrão ERC-20)."
    )
    keyboard = {"inline_keyboard": [[{"text": "📘 Leia nosso Whitepaper", "url": "https://rhapsody-coin.gitbook.io/rhapsody-protocol/"}]]}
    payload = {"chat_id": chat_id, "text": faq_text, "parse_mode": "Markdown", "disable_web_page_preview": True, "reply_markup": keyboard}
    requests.post(f"{TELEGRAM_API}/sendMessage", json=payload)

def send_social_media(chat_id):
    payload = {
        "chat_id": chat_id,
        "text": "📱 *Redes Sociais*:\n\n📸 [Instagram](https://instagram.com/rhapsodycoin)\n🔗 [Twitter/X](https://twitter.com/rhapsodycoin)\n💼 [LinkedIn](https://linkedin.com/company/rhapsody-coin)\n💬 [Telegram Oficial](https://t.me/rhapsodycoin)",
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

        if "chat_member" in data:
            chat_member = data["chat_member"]
            old_status = chat_member.get("old_chat_member", {}).get("status")
            new_status = chat_member.get("new_chat_member", {}).get("status")
            user = chat_member["new_chat_member"]["user"]
            chat_id = chat_member["chat"]["id"]

            if old_status in ("left", "kicked") and new_status == "member":
                user_id = user["id"]
                if str(user_id) == BOT_ID:
                    return "OK"
                first_name = user.get("first_name", "amigo")
                send_captcha(chat_id, user_id, first_name)
            return "OK"

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").lower().strip()
            from_user = message["from"]
            user_id = from_user["id"]
            first_name = from_user.get("first_name", "amigo")
            message_id = message["message_id"]

            # 🛠️ CORREÇÃO CRÍTICA: Remove o @nomedobot se existir (ex: "/ca@meubot" vira "/ca")
            if "@" in text:
                text = text.split("@")[0]

            # NOVO: Comando CA / Contrato (agora funciona mesmo com o @ do Telegram)
            if text in ["ca", "!ca", "/ca", "contrato", "contract", "endereço", "address", "endereco"]:
                send_contract(chat_id, reply_to_message_id=message_id)
                return "OK"

            if text == "/start" and message["chat"]["type"] == "private":
                send_welcome(chat_id, first_name)
                return "OK"

            if text == "/start" and message["chat"]["type"] != "private":
                reply = {"chat_id": chat_id, "text": "👋 Olá! Para ver todas as opções, envie /start em uma conversa privada comigo.", "reply_to_message_id": message_id}
                requests.post(f"{TELEGRAM_API}/sendMessage", json=reply)
                return "OK"

            for trigger in TRIGGERS:
                if trigger in text:
                    keyboard = {"inline_keyboard": [[{"text": "🛒 Vá para a Loja", "url": "https://rhapsody.criptocash.app/"}]]}
                    payload = {
                        "chat_id": chat_id,
                        "video": "BAACAgEAAxkBAAMyaTtJds7IEDJZKrPlUClLPkQ6gdsAAsMGAAKQcthFypomT3bj9iM2BA",
                        "caption": "🎥 Aqui está como comprar $RHAP!",
                        "reply_markup": keyboard,
                        "reply_to_message_id": message_id
                    }
                    requests.post(f"{TELEGRAM_API}/sendVideo", json=payload)
                    break
            return "OK"

        if "callback_query" in data:
            callback = data["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            data_value = callback["data"]
            from_user_id = callback["from"]["id"]

            if data_value.startswith("captcha_"):
                try:
                    target_user_id = int(data_value.split("_", 1)[1])
                    user_data = pending_users.get(target_user_id)
                    if from_user_id == target_user_id and user_data:
                        requests.post(f"{TELEGRAM_API}/deleteMessage", json={"chat_id": chat_id, "message_id": callback["message"]["message_id"]})
                        pending_users.pop(target_user_id, None)
                        first_name = callback["from"].get("first_name", "amigo")
                        send_welcome(chat_id, first_name)
                        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback["id"], "text": "✅ Bem-vindo à Comunidade Rhapsody!", "show_alert": False})
                    else:
                        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback["id"], "text": "❌ Este CAPTCHA não é para você.", "show_alert": True})
                except Exception as e:
                    print(f"[ERROR] Erro no captcha: {e}")
                return "OK"

            requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
            if data_value == "faq":
                send_faq(chat_id)
            elif data_value == "redes_sociais":
                send_social_media(chat_id)
            return "OK"

        return "OK"

    except Exception as e:
        print(f"[CRITICAL ERROR] {e}")
        return "OK"

@app.route("/")
def home():
    return "✅ Bot ativo! | Rhapsody Protocol — Gamificação e engajamento digital."

@app.route("/setwebhook")
def set_webhook():
    webhook_url = f"https://{request.host}/{TOKEN}"
    payload = {"url": webhook_url, "allowed_updates": ["message", "callback_query", "chat_member"]}
    response = requests.post(f"https://api.telegram.org/bot{TOKEN}/setWebhook", json=payload)
    return f"Webhook configurado para: {webhook_url}\nResposta: {response.json()}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
