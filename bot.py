import telebot
import os
from openai import OpenAI
from docx import Document
import pymupdf

# ================== CONFIG ==================
TOKEN = "8618790959:AAGpQJDuGBGLPjco0zZUqUYut6YfVdrwWuw"
GROQ_API_KEY = "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"

ALLOWED_USERS = [7699748754, 8165376014]

# Configuración de Groq
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

bot = telebot.TeleBot(TOKEN)
user_memory = {}

@bot.message_handler(commands=['start'])
def start(message):
    if message.from_user.id not in ALLOWED_USERS:
        bot.reply_to(message, f"🚫 No autorizado.\nTu ID: {message.from_user.id}")
        return
    bot.reply_to(message, "✅ ¡Bot privado activado con **Groq (Llama 3.3 70B)**!\n\n"
                         "Puedes enviarme:\n"
                         "• Texto normal\n"
                         "• Archivos PDF\n"
                         "• Archivos Word (.docx)\n\n"
                         "Usa /clear para borrar la memoria.")

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
    if len(user_memory[user_id]) > 25:
        user_memory[user_id] = user_memory[user_id][-25:]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",   # Modelo potente y rápido
            messages=[{"role": "system", "content": "Eres un tutor universitario experto, claro, motivador y preciso. Siempre responde en español de forma útil para estudiantes."}] + user_memory[user_id],
            temperature=0.7,
            max_tokens=2048
        )
        reply = response.choices[0].message.content
        user_memory[user_id].append({"role": "assistant", "content": reply})
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"❌ Error con Groq: {str(e)[:180]}")

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
            doc = pymupdf.open(file_name)
            text = "\n".join([page.get_text() for page in doc])
        elif file_name.endswith('.docx'):
            doc = Document(file_name)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        if text.strip():
            prompt = f"""Analiza este documento académico detalladamente:

{text[:100000]}

Responde con este formato:
- **Resumen claro y conciso**
- **Puntos clave más importantes**
- **Conceptos fundamentales**
- **Sugerencias para estudiar o preparar exámenes**"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Eres un tutor experto en analizar documentos académicos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=2048
            )
            bot.reply_to(message, response.choices[0].message.content)
        else:
            bot.reply_to(message, "❌ No pude extraer texto del archivo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error procesando archivo: {str(e)[:180]}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

print("🤖 Bot con Groq (Llama 3.3 70B) iniciado correctamente")
bot.infinity_polling()
