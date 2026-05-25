import requests
from bs4 import BeautifulSoup
import time
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys

# =====================================================================
# 1. CREDENCIALES DE TIENDANUBE (PORTAL DE PARTNERS - INTEGRACIÓN REAL)
# =====================================================================
STORE_ID = "pickmeba"
APP_ID = "32611"
CLIENT_SECRET = "8cff55e9ba26a11756cfef805a5aefd6006e8bfe0e87d7b3"  

TIENDANUBE_HEADERS = {
    "X-App-Id": APP_ID,
    "Authentication": f"bearer {CLIENT_SECRET}",
    "User-Agent": "SyncStockpickme (contacto@pickmeba.com.ar)",
    "Content-Type": "application/json"
}

# =====================================================================
# 2. FUNCIONES DE SINCRONIZACIÓN DE STOCK
# =====================================================================
def obtener_mis_productos_activos():
    url_endpoint = f"https://api.tiendanube.com/v1/{STORE_ID}/products?status=published&per_page=100"
    try:
        response = requests.get(url_endpoint, headers=TIENDANUBE_HEADERS)
        if response.status_code == 200:
            return response.json()
        print(f"✗ Estado de respuesta API Tiendanube: {response.status_code}")
        return []
    except Exception as e:
        print(f"✗ Error de conexión con Tiendanube: {e}")
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
    requests.put(url_endpoint, json=payload, headers=TIENDANUBE_HEADERS)

# Bucle continuo que corre todos los días de forma automática
def bucle_sincronizador_diario():
    while True:
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
                if stock_en_vita:
                    print(f"   ✓ Stock detectado en Vita: {stock_en_vita}", flush=True)
                    for variante in producto['variants']:
                        talle_mio = variante['values'][0]['es'].strip()
                        if talle_mio in stock_en_vita:
                            stock_real = stock_en_vita[talle_mio]
                            if variante['stock'] != stock_real:
                                print(f"   --> Cambiando Talle {talle_mio}: De {variante['stock']} u. a {stock_real} u.", flush=True)
                                actualizar_stock_tiendanube(producto['id'], variante['id'], stock_real)
                else:
                    print("   ? No se encontró enlace directo en Vita. Saltando...", flush=True)
                print("-" * 50, flush=True)
                time.sleep(1)
        else:
            print("✗ No se pudieron recuperar productos. Revisando credenciales...", flush=True)
        
        print("\nSincronización finalizada. Próximo escaneo en 24 horas...", flush=True)
        time.sleep(86400)

# Servidor HTTP básico obligatorio para mantener la cuenta GRATIS en Render
class ServidorSoporte(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Sincronizador Pick Me - Online y Ejecutando Gratis.")
    def log_message(self, format, *args):
        # Evita llenar la pantalla con las conexiones de Tiendanube y prioriza ver el stock
        return

def iniciar_servidor_web():
    server = HTTPServer(('0.0.0.0', 10000), ServidorSoporte)
    server.serve_forever()

if __name__ == "__main__":
    print("Encediendo Sincronizador Automático Pick Me...", flush=True)
    
    # 1. Lanzamos el bucle del stock en un hilo paralelo e inmediato
    proceso_stock = Thread(target=bucle_sincronizador_diario)
    proceso_stock.daemon = True
    proceso_stock.start()
    
    # 2. Dejamos el servidor web corriendo de fondo para Render
    iniciar_servidor_web()
