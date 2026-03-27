import telebot
import os
from openai import OpenAI
from docx import Document
import pymupdf  # ← Cambiado aquí (correcto en 2026)

# ================== CONFIG ==================
TOKEN = "8618790959:AAGpQJDuGBGLPjco0zZUqUYut6YfVdrwWuw"
DEEPSEEK_API_KEY = "sk-6406d64749604368a24b3b3a34fc162d"

# IDs correctos (cámbialos si es necesario)
ALLOWED_USERS = [7699748754, 8165376014]

client = OpenAI(
    base_url="https://api.deepseek.com",
    api_key=DEEPSEEK_API_KEY
)

bot = telebot.TeleBot(TOKEN)
user_memory = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, f"🚫 No autorizado.\nTu ID: {message.from_user.id}")
        return
    bot.reply_to(message, "✅ ¡Bot privado con DeepSeek activado!\n\nEnvía texto, PDF o Word (.docx).\nUsa /clear para borrar la memoria.")

@bot.message_handler(commands=['clear'])
def clear(message):
    if message.from_user.id in ALLOWED_USERS:
        user_memory.pop(message.from_user.id, None)
        bot.reply_to(message, "🧹 Memoria borrada.")

# ================== MENSAJES DE TEXTO ==================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    user_id = message.from_user.id
    if user_id not in user_memory:
        user_memory[user_id] = []
    
    user_memory[user_id].append({"role": "user", "content": message.text})
    if len(user_memory[user_id]) > 25:   # Reduje un poco para ahorrar tokens
        user_memory[user_id] = user_memory[user_id][-25:]

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",   # Prueba también "deepseek-reasoner" si quieres razonamiento más profundo
            messages=[{"role": "system", "content": "Eres un tutor universitario experto, claro, motivador y preciso. Siempre responde en español."}] + user_memory[user_id],
            temperature=0.7,
            max_tokens=2048
        )
        reply = response.choices[0].message.content
        user_memory[user_id].append({"role": "assistant", "content": reply})
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"❌ Error con DeepSeek: {str(e)[:180]}")

# ================== DOCUMENTOS (PDF y Word) ==================
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.from_user.id not in ALLOWED_USERS:
        return

    file_name = message.document.file_name.lower()
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with open(file_name, 'wb') as f:
        f.write(downloaded)

    bot.reply_to(message, "📄 Analizando documento... espera un momento.")

    try:
        text = ""
        if file_name.endswith('.pdf'):
            doc = pymupdf.open(file_name)          # ← Aquí está el cambio importante
            text = "\n".join([page.get_text() for page in doc])
        elif file_name.endswith('.docx'):
            doc = Document(file_name)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        if text.strip():
            prompt = f"""Analiza este documento académico con detalle:

{text[:110000]}

Responde con:
- Resumen claro y conciso
- Puntos clave más importantes
- Conceptos fundamentales
- Sugerencias para estudiar o preparar exámenes"""

            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "Eres un tutor experto en análisis de documentos académicos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=2048
            )
            bot.reply_to(message, response.choices[0].message.content)
        else:
            bot.reply_to(message, "❌ No pude extraer texto del archivo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error procesando el archivo: {str(e)[:200]}")
    finally:
        # Borramos el archivo temporal
        if os.path.exists(file_name):
            os.remove(file_name)

print("🤖 Bot con DeepSeek iniciado correctamente")
bot.infinity_polling()