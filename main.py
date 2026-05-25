import requests
from bs4 import BeautifulSoup
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# =====================================================================
# 1. CREDENCIALES DE CONFIGURACIÓN (PORTAL DE PARTNERS)
# =====================================================================
STORE_ID = "pickmeba"
APP_ID = "32611"
CLIENT_SECRET = "8cff55e9ba26a11756cfef805a5aefd6006e8bfe0e87d7b3"  

# Variable global donde el script guardará el Token definitivo apenas hagas clic
ACCESS_TOKEN_REAL = None

def obtener_headers():
    global ACCESS_TOKEN_REAL
    return {
        "X-App-Id": APP_ID,
        "Authentication": f"bearer {ACCESS_TOKEN_REAL}",
        "User-Agent": "SyncStockpickme (contacto@pickmeba.com.ar)",
        "Content-Type": "application/json"
    }

# =====================================================================
# 2. FUNCIONES DE SINCRONIZACIÓN DE STOCK
# =====================================================================
def obtener_mis_productos_activos():
    url_endpoint = f"https://api.tiendanube.com/v1/{STORE_ID}/products?status=published&per_page=100"
    try:
        response = requests.get(url_endpoint, headers=obtener_headers())
        if response.status_code == 200:
            return response.json()
        print(f"✗ Estado de respuesta API Tiendanube: {response.status_code}", flush=True)
        return []
    except Exception as e:
        print(f"✗ Error de conexión con Tiendanube: {e}", flush=True)
        return []

def obtener_stock_proveedor(nombre_producto_slug):
    nombre_limpio = nombre_producto_slug.split('-')[0] 
    url_posible = f"https://vita-mayorista.com.ar/productos/bota-texana-cuero-{nombre_limpio}/"
    headers_navegador = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url_posible, headers=headers_navegador, timeout=10)
        if response.status_code == 404:
            url_posible = f"https://vita-mayorista.com.ar/productos/{nombre_limpio}/"
            response = requests.get(url_posible, headers=headers_navegador, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, 'html.parser')
        stock_proveedor = {}
        select_variantes = soup.find('select', class_=['product-variant-select', 'form-control'])
        if select_variantes:
            for option in select_variantes.find_all('option'):
                texto_opcion = option.text.strip()
                if "(" in texto_opcion:
                    talle = texto_opcion.split("(")[0].strip()
                    detalles_stock = texto_opcion.split("(")[1].lower()
                    cantidad = 0 if "sin stock" in detalles_stock else int(''.join(filter(str.isdigit, detalles_stock)))
                    stock_proveedor[talle] = cantidad
        return stock_proveedor
    except:
        return None

def actualizar_stock_tiendanube(product_id, variant_id, nuevo_stock):
    url_endpoint = f"https://api.tiendanube.com/v1/{STORE_ID}/products/{product_id}/variants/{variant_id}"
    payload = {"stock": nuevo_stock}
    requests.put(url_endpoint, json=payload, headers=obtener_headers())

def bucle_sincronizador_diario():
    global ACCESS_TOKEN_REAL
    while True:
        if not ACCESS_TOKEN_REAL:
            print("[Esperando] El script está listo. Esperando que hagas la instalación para capturar el Token...", flush=True)
            time.sleep(10)
            continue
            
        print("\n==================================================", flush=True)
        print("   INICIANDO ACTUALIZACIÓN AUTOMÁTICA DE STOCK    ", flush=True)
        print("==================================================\n", flush=True)
        
        mis_productos = obtener_mis_productos_activos()
        if mis_productos:
            print(f"-> ¡Conexión exitosa! {len(mis_productos)} productos encontrados en Pick Me.\n", flush=True)
            for producto in mis_productos:
                slug_mio = producto['handle']['es']
                print(f"Procesando: {producto['name']['es']}...", flush=True)
                
                stock_en_vita = obtener_stock_proveedor(slug_mio)
                if stock_en
