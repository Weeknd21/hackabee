from google import genai
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
import PyPDF2
import os

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

def cargar_contexto():
    """Carga contexto de archivos .toon y PDFs"""
    contexto_completo = ""
    
    # Cargar archivo .toon
    if os.path.exists("contexto.toon"):
        with open("contexto.toon", "r", encoding="utf-8") as f:
            contexto_completo += f.read() + "\n\n"
    
    # Cargar PDFs de la carpeta 'pdfs'
    pdf_folder = "pdfs"
    if os.path.exists(pdf_folder):
        for filename in os.listdir(pdf_folder):
            if filename.lower().endswith('.pdf'):
                pdf_path = os.path.join(pdf_folder, filename)
                try:
                    texto_pdf = extraer_texto_pdf(pdf_path)
                    contexto_completo += f"=== CONTENIDO DE {filename} ===\n{texto_pdf}\n\n"
                except Exception as e:
                    print(f"Error procesando {filename}: {e}")
    
    return contexto_completo

def extraer_texto_pdf(ruta_pdf):
    """Extrae texto de un archivo PDF"""
    texto = ""
    with open(ruta_pdf, 'rb') as archivo:
        lector_pdf = PyPDF2.PdfReader(archivo)
        for pagina in lector_pdf.pages:
            texto += pagina.extract_text() + "\n"
    return texto

# Cargar contexto al iniciar el servidor
CONTEXTO = cargar_contexto()
print(f"Contexto cargado: {len(CONTEXTO)} caracteres")

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
            model="gemini-2.5-flash-lite-preview-09-2025",
            contents=prompt
        )

        for chunk in stream:
            if chunk.text:
                yield chunk.text

    return Response(stream_response(), mimetype="text/plain")

if __name__ == "__main__":
    print("Servidor corriendo en http://localhost:5000/chat")
    app.run(host="0.0.0.0", port=5000, debug=True)