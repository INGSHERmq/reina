import telebot
import os
from openai import OpenAI
from docx import Document
import pymupdf

# ================== CONFIG ==================
TOKEN = "8618790959:AAGpQJDuGBGLPjco0zZUqUYut6YfVdrwWuw"
GROQ_API_KEY = "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"

ALLOWED_USERS = [7699748754, 8165376014]

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
    bot.reply_to(message, "✅ **¡Hola! Soy tu IA privada para estudiar, fui creado por Sherry y**\n\n"
                         "Puedo ayudarte con:\n"
                         "• Explicaciones claras\n"
                         "• Resúmenes\n"
                         "• Análisis de PDFs y Word\n"
                         "• Investigación\n\n"
                         "Comandos útiles:\n"
                         "/clear → Borrar memoria\n"
                         "/ayuda → Ver todos los comandos\n"
                         "De momento no puedo analizar ni generar imagenes, le falta nivel a mi creador\n\n")

@bot.message_handler(commands=['clear'])
def clear(message):
    if message.from_user.id in ALLOWED_USERS:
        user_memory.pop(message.from_user.id, None)
        bot.reply_to(message, "🧹 Memoria borrada correctamente.")

@bot.message_handler(commands=['ayuda'])
def ayuda(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    bot.reply_to(message, "📋 **Comandos disponibles:**\n\n"
                         "/start - Iniciar el bot\n"
                         "/clear - Borrar memoria de conversación\n"
                         "/ayuda - Mostrar esta ayuda\n\n"
                         "Solo envíame texto, PDF o archivos Word y te ayudo.")

# ================== TEXTO ==================
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.from_user.id not in ALLOWED_USERS:
        return
    
    user_id = message.from_user.id
    if user_id not in user_memory:
        user_memory[user_id] = []
    
    user_memory[user_id].append({"role": "user", "content": message.text})
    if len(user_memory[user_id]) > 28:
        user_memory[user_id] = user_memory[user_id][-28:]

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Eres un excelente tutor universitario. Responde siempre en español, de forma clara, motivadora y útil para estudiantes."}] + user_memory[user_id],
            temperature=0.7,
            max_tokens=2048
        )
        reply = response.choices[0].message.content
        user_memory[user_id].append({"role": "assistant", "content": reply})
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:150]}")

# ================== DOCUMENTOS ==================
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.from_user.id not in ALLOWED_USERS:
        return

    file_name = message.document.file_name.lower()
    file_info = bot.get_file(message.document.file_id)
    downloaded = bot.download_file(file_info.file_path)

    with open(file_name, 'wb') as f:
        f.write(downloaded)

    bot.reply_to(message, "📄 Analizando documento... dame un momento.")

    try:
        text = ""
        if file_name.endswith('.pdf'):
            doc = pymupdf.open(file_name)
            text = "\n".join([page.get_text() for page in doc])
        elif file_name.endswith('.docx'):
            doc = Document(file_name)
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])

        if text.strip():
            prompt = f"""Analiza este documento académico con cuidado:

{text[:110000]}

Devuélveme en español:
- **Resumen claro**
- **Puntos clave**
- **Conceptos importantes**
- **Sugerencias para estudiar**"""

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Eres un tutor experto analizando documentos académicos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.65,
                max_tokens=2048
            )
            bot.reply_to(message, response.choices[0].message.content)
        else:
            bot.reply_to(message, "❌ No pude extraer texto del archivo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error al procesar el archivo: {str(e)[:150]}")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

print("🤖 Bot con Groq iniciado correctamente - Versión mejorada")
bot.infinity_polling()
