from flask import Flask, request
import requests
import os
import threading
import time

app = Flask(__name__)
TOKEN = os.getenv("TOKEN")
BOT_ID = os.getenv("BOT_ID", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"

# Armazena última mensagem de boas-vindas por chat_id
last_welcome_message = {}

# Armazena usuários aguardando confirmação: {user_id: {"chat_id": ..., "message_id": ...}}
pending_users = {}

# Gatilhos de compra
TRIGGERS = ["como comprar", "onde comprar", "quero comprar", "comprar rhap", "como compra"]

# --- FUNÇÕES ---
def remove_user_if_pending(chat_id, user_id, message_id):
    """Remove usuário se não confirmar em 40s e apaga a mensagem do CAPTCHA"""
    time.sleep(40)
    if user_id in pending_users:
        try:
            # Apagar a mensagem do CAPTCHA
            requests.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": message_id
            })
            # Expulsar o usuário do grupo (kick via ban + unban)
            requests.post(f"{TELEGRAM_API}/banChatMember", json={"chat_id": chat_id, "user_id": user_id})
            time.sleep(0.5)
            requests.post(f"{TELEGRAM_API}/unbanChatMember", json={"chat_id": chat_id, "user_id": user_id})
        except:
            pass
        pending_users.pop(user_id, None)

def send_captcha(chat_id, user_id, first_name):
    """Envia CAPTCHA no grupo"""
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

    # Apaga mensagem anterior
    if chat_id in last_welcome_message:
        try:
            requests.post(f"{TELEGRAM_API}/deleteMessage", json={
                "chat_id": chat_id,
                "message_id": last_welcome_message[chat_id]
            })
        except:
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
            [{"text": "🌐 Site oficial", "url": "https://www.rhapsodycoin.com"}],
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
        "📌 *Aqui está a lista de perguntas frequentes atualizada sobre o Rhapsody Protocol*\n\n"
        "*Em que situação está o projeto atualmente?*\n"
        "O Rhapsody Protocol segue em pré-venda ativa na CriptoCash (mesmo link) até nova data, que será anunciada em breve. O lançamento do token $RHAP, originalmente previsto para 23/01 na Brasil Bitcoin (BBT), foi adiado — a nova data será definida em reunião interna em 27/01.\n\n" 
        "*O token $RHAP já foi lançado?*\n"
        "Não, o token $RHAP ainda não foi lançado publicamente. Ele será disponibilizado oficialmente na Brasil Bitcoin (BBT) após o encerramento da pré-venda estendida, com a data de listagem a ser confirmada em 27/01/2026.\n"       
        "*Em qual rede o projeto e o token serão lançados?*\n"
        "O Rhapsody Protocol e o token $RHAP operam na rede Ethereum, seguindo o padrão ERC-20. Essa escolha garante compatibilidade com wallets amplamente utilizadas, segurança e acesso ao ecossistema DeFi consolidado.\n\n"
        "*Qual o supply total do token $RHAP?*\n"
        "O supply total é fixo em 1.000.000.000 (1 bilhão) de tokens RHAP. Não haverá novas emissões além desse limite, garantindo escassez programada.\n\n"
        "*Qual será a função do token $RHAP?*\n"
        "O $RHAP é o token utilitário central do ecossistema. Ele será usado para:\n"
        "- Acessar e interagir com aplicações gamificadas (como Musicplayce),\n"
        "- Participar de mecânicas de gacha, staking e recompensas,\n"
        "- Mintar NFTs certificados com utilidade real,\n"
        "- Futuramente, votar em decisões da DAO e pagar por serviços dentro do protocolo.\n\n"
        "*Qual a função dos usuários nessa fase do projeto?*\n"
        "Nesta fase, os usuários podem:\n"
        "- Participar da pré-venda,\n"
        "- Se preparar para o lançamento oficial,\n"
        "- Acompanhar os cases de uso como a Musicplayce (apenas um exemplo de aplicação),\n"
        "- *Tornar-se um parceiro de divulgação*: se você tem um canal, comunidade ou audiência e quer promover o Rhapsody Protocol, inscreva-se no programa de afiliados e ganhe até *15% de comissão* sobre todas as vendas geradas por você!\n\n"
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

# --- WEBHOOK ---
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()

    if data and "message" in data:
        message = data["message"]
        chat_id = message["chat"]["id"]

        # Novo membro → CAPTCHA
        if "new_chat_member" in message:
            new_member = message["new_chat_member"]
            user_id = new_member.get("id")
            if str(user_id) == BOT_ID:
                return "OK"
            first_name = new_member.get("first_name", "amigo")
            send_captcha(chat_id, user_id, first_name)
            return "OK"

        # Mensagens de texto
        if "text" in message:
            text = message["text"].lower().strip()
            first_name = message["from"].get("first_name", "amigo")

            if text == "/start":
                if message["chat"]["type"] == "private":
                    send_welcome(chat_id, first_name)
                else:
                    reply = {
                        "chat_id": chat_id,
                        "text": "👋 Olá! Para ver todas as opções, envie /start em uma conversa privada comigo.",
                        "reply_to_message_id": message["message_id"]
                    }
                    requests.post(f"{TELEGRAM_API}/sendMessage", json=reply)
                return "OK"

            # Gatilhos de compra
            for trigger in TRIGGERS:
                if trigger in text:
                    keyboard = {"inline_keyboard": [[{"text": "🛒 Vá para a Loja", "url": "https://rhapsody.criptocash.app/"}]]}
                    payload = {
                        "chat_id": chat_id,
                        "video": "BAACAgEAAxkBAAMyaTtJds7IEDJZKrPlUClLPkQ6gdsAAsMGAAKQcthFypomT3bj9iM2BA",
                        "caption": "🎥 Aqui está como comprar $RHAP!",
                        "reply_markup": keyboard
                    }
                    requests.post(f"{TELEGRAM_API}/sendVideo", json=payload)
                    break
            return "OK"

    # Callbacks (botões)
    if data and "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        data_value = callback["data"]
        from_user_id = callback["from"]["id"]

        # CAPTCHA
        if data_value.startswith("captcha_"):
            try:
                target_user_id = int(data_value.split("_", 1)[1])
                user_data = pending_users.get(target_user_id)
                if from_user_id == target_user_id and user_data:
                    # Apaga o CAPTCHA
                    requests.post(f"{TELEGRAM_API}/deleteMessage", json={
                        "chat_id": chat_id,
                        "message_id": callback["message"]["message_id"]
                    })
                    # Remove da lista pendente
                    pending_users.pop(target_user_id, None)
                    # Envia boas-vindas
                    first_name = callback["from"].get("first_name", "amigo")
                    send_welcome(chat_id, first_name)
                    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
                        "callback_query_id": callback["id"],
                        "text": "✅ Bem-vindo à Comunidade Rhapsody!",
                        "show_alert": False
                    })
                else:
                    requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={
                        "callback_query_id": callback["id"],
                        "text": "❌ Este CAPTCHA não é para você.",
                        "show_alert": True
                    })
            except:
                pass
            return "OK"

        # Outros botões
        requests.post(f"{TELEGRAM_API}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
        if data_value == "faq":
            send_faq(chat_id)
        elif data_value == "redes_sociais":
            send_social_media(chat_id)
        return "OK"

    return "OK"

# --- ROTAS AUXILIARES ---
@app.route("/")
def home():
    return "✅ Bot ativo! | Rhapsody Protocol — Gamificação e engajamento digital."

@app.route("/setwebhook")
def set_webhook():
    webhook_url = f"https://{request.host}/{TOKEN}"
    response = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/setWebhook",
        data={"url": webhook_url}
    )
    return f"Webhook configurado para: {webhook_url}\nResposta: {response.json()}"
