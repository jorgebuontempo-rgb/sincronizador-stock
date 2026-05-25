import requests
from bs4 import BeautifulSoup
import time

# =====================================================================
# 1. CONFIGURACIÓN DE CREDENCIALES (SISTEMA DE CANJE EN CALIENTE)
# =====================================================================
STORE_ID = "pickmeba"
APP_ID = "32611"

# ⚠️ 1. PEGA ACÁ TU CLIENT SECRET (El código de los puntitos de Partners)
CLIENT_SECRET = "fa20c07b6ddbb8cc7ad74119343f9f930bbe88df6f189517"  

# ⚠️ 2. PEGA ACÁ EL CÓDIGO NUEVO QUE ACABAS DE SACAR DE LA URL
CODE_FROM_URL = "84b3a7dbcf17250fc45b6f41530eb943f1d85f4b"

# =====================================================================
# PROCESO DE OBTENCIÓN DEL ACCESS TOKEN REAL
# =====================================================================
print("Solicitando Access Token oficial a Tiendanube...")
token_url = "https://www.tiendanube.com/apps/authorize/token"
token_payload = {
    "client_id": APP_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "authorization_code",
    "code": CODE_FROM_URL
}

ACCESS_TOKEN = None
try:
    token_response = requests.post(token_url, json=token_payload, timeout=15)
    if token_response.status_code == 200:
        ACCESS_TOKEN = token_response.json().get("access_token")
        print("   ✓ ¡Token permanente generado con éxito!")
    else:
        print(f"   ✗ Error en el canje ({token_response.status_code}): {token_response.text}")
except Exception as e:
    print(f"Error de conexión: {e}")

# =====================================================================
# 2. PROCESO DE SINCRONIZACIÓN AUTOMÁTICA DE STOCK
# =====================================================================
if ACCESS_TOKEN:
    TIENDANUBE_HEADERS = {
        "Authentication": f"bearer {ACCESS_TOKEN}",
        "User-Agent": "SyncStockpickme (contacto@pickmeba.com.ar)",
        "Content-Type": "application/json"
    }

    # FUNCIÓN INTERNA PARA RASPAR VITA MAYORISTA
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
            select_variantes = soup.find('select', class_='product-variant-select')
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

    print("\n==================================================")
    print("   INICIANDO ACTUALIZACIÓN TOTAL DE STOCK         ")
    print("==================================================")
    
    url_endpoint = f"https://api.tiendanube.com/v1/{STORE_ID}/products?status=published&per_page=100"
    res_productos = requests.get(url_endpoint, headers=TIENDANUBE_HEADERS)
    
    if res_productos.status_code == 200:
        mis_productos = res_productos.json()
        print(f"-> ¡Conexión exitosa! {len(mis_productos)} productos encontrados.\n")
        
        for producto in mis_productos:
            slug_mio = producto['handle']['es']
            print(f"Sincronizando: {producto['name']['es']}...")
            
            stock_en_vita = obtener_stock_proveedor(slug_mio)
            if stock_en_vita:
                print(f"   ✓ Stock en Vita: {stock_en_vita}")
                for variante in producto['variants']:
                    talle_mio = variante['values'][0]['es'].strip()
                    if talle_mio in stock_en_vita:
                        stock_real = stock_en_vita[talle_mio]
                        if variante['stock'] != stock_real:
                            print(f"   --> Cambiando Talle {talle_mio}: De {variante['stock']} u. a {stock_real} u.")
                            actualizar_stock_tiendanube(producto['id'], variante['id'], stock_real)
            else:
                print("   ? No encontrado en Vita. Saltando...")
            print("-" * 50)
            time.sleep(1)
            
        print("==================================================")
        print("   ¡SINCRONIZACIÓN COMPLETA PARA TU WEB!          ")
        print("==================================================")
    else:
        print(f"   ✗ Error final de la API ({res_productos.status_code}): {res_productos.text}")
else:
    print("No se pudo iniciar la sincronización porque el token no es válido o ya venció.")