from google import genai
from flask import Flask, request, Response, jsonify
from flask_cors import CORS

app = Flask(__name__)

# CORS robusto
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "allow_headers": "*",
        "methods": ["POST", "GET", "OPTIONS"]
    }
})

API_KEY = "AIzaSyANG6cABgPV7N0QK0ElY6jZcNZ5cWMt1dI"
client = genai.Client(api_key=API_KEY)

# Cargar contexto
with open("contexto.toon", "r", encoding="utf-8") as f:
    CONTEXTO = f.read()


@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return jsonify({"message": "OK"}), 200

    data = request.json
    user_message = data.get("message", "")

    prompt = f"""
=== CONTEXTO ===
{CONTEXTO}

=== USUARIO ===
{user_message}

Responde naturalmente usando el contexto.
"""

    def stream_response():
        stream = client.models.generate_content_stream(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )

        for chunk in stream:
            if chunk.text:
                yield chunk.text

    return Response(stream_response(), mimetype="text/plain")


if __name__ == "__main__":
    print("Servidor corriendo en http://localhost:5000/chat")
    app.run(host="0.0.0.0", port=5000, debug=True)
