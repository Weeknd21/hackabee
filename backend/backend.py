from google import genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5500", "http://127.0.0.1:5500"]}})


API_KEY = "AIzaSyANG6cABgPV7N0QK0ElY6jZcNZ5cWMt1dI"

# Inicializar cliente Gemini moderno
client = genai.Client(api_key=API_KEY)

# Cargar tu archivo .toon como contexto permanente
with open("contexto.toon", "r", encoding="utf-8") as f:
    CONTEXTO = f.read()


@app.post("/chat")
def chat():
    data = request.get_json()
    user_message = data.get("message", "")

    prompt = f"""
=== CONTEXTO DEL CHATBOT ===
{CONTEXTO}

=== MENSAJE DEL USUARIO ===
{user_message}

Responde de forma natural y útil usando el contexto cuando sea relevante.
    """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]   # ← CORRECCIÓN CLAVE
    )

    return jsonify({
        "response": response.text
    })


if __name__ == "__main__":
    print("🔥 Servidor activo en http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
