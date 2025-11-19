import requests
from bs4 import BeautifulSoup
import json
import io
from pypdf import PdfReader
import time
from urllib.parse import urljoin

# URL base
BASE_URL = "http://www.caecis.ugto.mx/caecis/pages/index.asp"
ROOT_DOMAIN = "http://www.caecis.ugto.mx"

# Configuración de headers para parecer un navegador real (evita bloqueos)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_soup(url):
    """Descarga y parsea una URL con manejo de errores."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        # Forzar detección de encoding correcta
        response.encoding = response.apparent_encoding 
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"   [!] Error accediendo a {url}: {e}")
        return None

def extract_pdf_text(url):
    """Descarga y extrae texto de un PDF."""
    try:
        print(f"      ... Descargando PDF: {url.split('/')[-1]}")
        response = requests.get(url, headers=HEADERS, timeout=20)
        with io.BytesIO(response.content) as f:
            reader = PdfReader(f)
            text = ""
            if reader.pages:
                text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            return text
    except Exception as e:
        return f"[Error leyendo PDF: {e}]"

def crawl_deep():
    print(f"--- INICIANDO SCRAPING PROFUNDO EN: {BASE_URL} ---")
    soup = get_soup(BASE_URL)
    if not soup: return

    base_de_conocimiento = []
    visited_urls = set() # Para evitar ciclos
    
    # 1. Obtener enlaces del Menú Principal
    main_links = soup.find_all('a', href=True)
    print(f"Encontrados {len(main_links)} enlaces en el menú principal.")

    for i, link in enumerate(main_links):
        href = link['href']
        full_url = urljoin(BASE_URL, href) # Une la URL base con el enlace relativo

        # Filtros de seguridad
        if full_url in visited_urls: continue
        if "javascript" in href or "#" in href: continue
        if not full_url.startswith(ROOT_DOMAIN): continue # No salir del sitio de la UG

        visited_urls.add(full_url)

        # Obtener título del trámite
        title = link.get_text(strip=True)
        if not title:
            img = link.find('img')
            title = img['alt'] if img and img.get('alt') else "Trámite sin nombre"

        print(f"\n[{i+1}/{len(main_links)}] Procesando: {title}")
        
        item_data = {
            "titulo": title,
            "url_origen": full_url,
            "texto_web": "",
            "pdfs_relacionados": []
        }

        # --- LÓGICA DE PROFUNDIDAD ---
        
        # CASO A: El enlace del menú es directo a un PDF
        if full_url.lower().endswith('.pdf'):
            content = extract_pdf_text(full_url)
            item_data["pdfs_relacionados"].append({
                "nombre_archivo": full_url.split('/')[-1],
                "url": full_url,
                "contenido": content
            })

        # CASO B: El enlace es una página web (.aspx, .asp, .html) -> ¡HAY QUE BUSCAR DENTRO!
        else:
            sub_soup = get_soup(full_url)
            if sub_soup:
                # 1. Extraer texto visible de la sub-página
                for tag in sub_soup(["script", "style", "nav", "footer"]):
                    tag.extract()
                item_data["texto_web"] = sub_soup.get_text(separator=' ', strip=True)

                # 2. BUSCAR PDFs DENTRO DE ESTA SUB-PÁGINA (Nivel 2)
                sub_links = sub_soup.find_all('a', href=True)
                for sub_link in sub_links:
                    sub_href = sub_link['href']
                    sub_full_url = urljoin(full_url, sub_href)
                    
                    # Si encontramos un PDF dentro de la página del trámite
                    if sub_full_url.lower().endswith('.pdf') and sub_full_url not in visited_urls:
                        visited_urls.add(sub_full_url) # Marcar como visitado
                        pdf_text = extract_pdf_text(sub_full_url)
                        
                        pdf_name = sub_link.get_text(strip=True)
                        if not pdf_name: pdf_name = sub_full_url.split('/')[-1]

                        item_data["pdfs_relacionados"].append({
                            "nombre_archivo": pdf_name,
                            "url": sub_full_url,
                            "contenido": pdf_text
                        })

        base_de_conocimiento.append(item_data)
        time.sleep(0.5) # Pausa respetuosa

    # Guardar JSON final
    print("\n--- GUARDANDO ARCHIVO GIGANTE ---")
    with open('base_datos_ugto_completa.json', 'w', encoding='utf-8') as f:
        json.dump(base_de_conocimiento, f, ensure_ascii=False, indent=4)
    
    print("¡Listo! Archivo 'base_datos_ugto_completa.json' generado con éxito.")

if __name__ == "__main__":
    crawl_deep()