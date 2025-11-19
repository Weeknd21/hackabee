import requests
from bs4 import BeautifulSoup
import json
import io
import pdfplumber
import re
import time
from urllib.parse import urljoin

# --- CONFIGURACIÓN ---
BASE_URL = "http://www.caecis.ugto.mx/caecis/pages/index.asp"
ROOT_DOMAIN = "http://www.caecis.ugto.mx"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# --- LÓGICA DE PARSEO ESTRUCTURADO (Para Kardex/Planes de Estudio) ---
def parse_structured_kardex(pdf_bytes):
    """
    Intenta extraer la estructura lógica (Materias, Créditos, Categorías)
    basándose en el formato visual de la UG.
    """
    data = {
        "tipo_documento": "PLAN_ESTUDIOS_ESTRUCTURADO",
        "programa_educativo": "No detectado",
        "requisitos_ingles": "No detectado",
        "contenido_estructurado": {}
    }
    
    current_category = "GENERAL"
    
    # Regex basado en tu ejemplo: UDA (3-4 letras + números) + Nombre + Créditos
    # Ejemplo: "NEL106001 Algebra Lineal 6"
    subject_pattern = re.compile(r'^([A-Z]{3,4}\w{5,7})\s+(.+?)\s+(\d{1,2})$')
    header_pattern = re.compile(r"(OBLIGATORIOS|OPTATIVAS|AREA)\s+([A-ZÁÉÍÓÚÑ\s]+)")
    
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            full_text_lines = []
            for page in pdf.pages:
                # x_tolerance ayuda a leer las tablas visuales correctamente
                text = page.extract_text(x_tolerance=2, y_tolerance=3)
                if text:
                    full_text_lines.extend(text.split('\n'))
            
            # Analizar línea por línea
            for line in full_text_lines:
                line = line.strip()
                
                if "Licenciatura en" in line and data["programa_educativo"] == "No detectado":
                    data["programa_educativo"] = line
                    continue
                
                if "Formas de Cumplir el Inglés" in line:
                    data["requisitos_ingles"] = line
                    continue

                # Detectar cambio de categoría (Ej: OBLIGATORIOS BÁSICA)
                header_match = header_pattern.search(line)
                if header_match and not subject_pattern.match(line):
                    current_category = f"{header_match.group(1)} {header_match.group(2)}".strip()
                    if current_category not in data["contenido_estructurado"]:
                        data["contenido_estructurado"][current_category] = []
                    continue

                # Detectar materia
                match = subject_pattern.search(line)
                if match:
                    subject_obj = {
                        "codigo": match.group(1),
                        "materia": match.group(2).strip(),
                        "creditos": int(match.group(3))
                    }
                    # Inicializar categoría si no existe
                    if current_category not in data["contenido_estructurado"]:
                        data["contenido_estructurado"][current_category] = []
                    
                    data["contenido_estructurado"][current_category].append(subject_obj)
    
        # Validación: Si no extrajimos ninguna materia, probablemente no era un Kardex
        if not data["contenido_estructurado"]:
            return None
            
        return data

    except Exception as e:
        print(f"      [!] Error intentando parseo estructurado: {e}")
        return None

# --- LÓGICA GENÉRICA (Para otros documentos) ---
def parse_generic_pdf(pdf_bytes):
    """Extracción de texto plano para documentos normales."""
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return {"tipo_documento": "TEXTO_PLANO", "contenido": text}
    except Exception as e:
        return {"tipo_documento": "ERROR", "contenido": f"Error leyendo PDF: {e}"}

# --- CONTROLADOR PRINCIPAL DE PDFs ---
def process_pdf_url(url):
    """Descarga el PDF y decide qué estrategia de lectura usar."""
    try:
        print(f"      ... Descargando PDF: {url.split('/')[-1]}")
        response = requests.get(url, headers=HEADERS, timeout=20)
        response.raise_for_status()
        pdf_bytes = response.content
        
        # 1. Intentar parseo estructurado (Kardex)
        structured_data = parse_structured_kardex(pdf_bytes)
        
        if structured_data:
            print("      [+] ¡Estructura de Plan de Estudios detectada y extraída!")
            return structured_data
        else:
            # 2. Si falla o no es Kardex, usar texto plano
            return parse_generic_pdf(pdf_bytes)
            
    except Exception as e:
        return {"tipo_documento": "ERROR_DESCARGA", "contenido": str(e)}

# --- CRAWLER (Igual que antes, pero llamando a la nueva lógica) ---
def get_soup(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = response.apparent_encoding
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"   [!] Error URL {url}: {e}")
        return None

def crawl_hybrid_system():
    print(f"--- INICIANDO SCRAPER HÍBRIDO EN: {BASE_URL} ---")
    soup = get_soup(BASE_URL)
    if not soup: return

    base_datos = []
    visited_urls = set()
    
    main_links = soup.find_all('a', href=True)
    
    for i, link in enumerate(main_links):
        href = link['href']
        full_url = urljoin(BASE_URL, href)

        if full_url in visited_urls or "javascript" in href or "#" in href: continue
        if not full_url.startswith(ROOT_DOMAIN): continue

        visited_urls.add(full_url)
        title = link.get_text(strip=True)
        if not title: 
            img = link.find('img')
            title = img['alt'] if img and img.get('alt') else "Sin título"

        print(f"\n[{i+1}/{len(main_links)}] Tema: {title}")

        entry = {
            "titulo_tema": title,
            "url_origen": full_url,
            "tipo": "web",
            "datos": {}
        }

        # CASO 1: Es un PDF directo
        if full_url.lower().endswith('.pdf'):
            entry["tipo"] = "pdf"
            entry["datos"] = process_pdf_url(full_url) # <--- AQUÍ LA MAGIA

        # CASO 2: Es una Web (buscamos PDFs dentro)
        else:
            sub_soup = get_soup(full_url)
            if sub_soup:
                # Limpiar HTML
                for tag in sub_soup(["script", "style", "nav", "footer"]): tag.extract()
                
                entry["datos"] = {
                    "texto_web": sub_soup.get_text(separator=' ', strip=True),
                    "documentos_adjuntos": []
                }
                
                # Buscar PDFs internos
                sub_links = sub_soup.find_all('a', href=True)
                for sub in sub_links:
                    sub_href = sub['href']
                    sub_full = urljoin(full_url, sub_href)
                    
                    if sub_full.lower().endswith('.pdf') and sub_full not in visited_urls:
                        visited_urls.add(sub_full)
                        pdf_name = sub.get_text(strip=True) or sub_full.split('/')[-1]
                        
                        print(f"   -> Encontrado documento interno: {pdf_name}")
                        pdf_data = process_pdf_url(sub_full) # <--- AQUÍ TAMBIÉN
                        
                        entry["datos"]["documentos_adjuntos"].append({
                            "nombre": pdf_name,
                            "url": sub_full,
                            "info_extraida": pdf_data
                        })

        base_datos.append(entry)
        time.sleep(1) # Pausa para no saturar

    # Guardar
    print("\n--- GUARDANDO JSON FINAL ---")
    with open('base_datos_ugto_inteligente.json', 'w', encoding='utf-8') as f:
        json.dump(base_datos, f, ensure_ascii=False, indent=4)
    print("Proceso terminado.")

if __name__ == "__main__":
    crawl_hybrid_system()