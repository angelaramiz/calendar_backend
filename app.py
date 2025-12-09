"""
Scraper API Universal con Flask y Selenium
Soporta: MercadoLibre, Amazon, Liverpool, Walmart, Coppel, Home Depot,
         Elektra, Costco, Sam's Club, Best Buy, Office Depot, y cualquier tienda online
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import json
from datetime import datetime, timezone
from urllib.parse import urlparse
import traceback
import time

app = Flask(__name__)
CORS(app)

# ============================================
# CONFIGURACIÓN DE SELENIUM
# ============================================
def get_chrome_driver(headless=True):
    """Crear instancia de Chrome con configuración óptima"""
    options = Options()
    
    if headless:
        options.add_argument('--headless=new')
    
    # Opciones para evitar detección
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--lang=es-MX')
    
    # Excluir switches de automatización
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    # Ejecutar script para ocultar webdriver
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


# ============================================
# DETECTAR PLATAFORMA Y TIENDA
# ============================================
PLATFORM_CONFIG = {
    'mercadolibre': {
        'patterns': ['mercadolibre', 'mercadolivre', 'meli.'],
        'currency': 'MXN',
        'store': 'MercadoLibre'
    },
    'amazon': {
        'patterns': ['amazon.com.mx', 'amazon.com', 'amzn.', 'a.co/'],
        'currency': 'MXN',
        'store': 'Amazon'
    },
    'liverpool': {
        'patterns': ['liverpool.com.mx'],
        'currency': 'MXN',
        'store': 'Liverpool'
    },
    'walmart': {
        'patterns': ['walmart.com.mx'],
        'currency': 'MXN',
        'store': 'Walmart'
    },
    'coppel': {
        'patterns': ['coppel.com'],
        'currency': 'MXN',
        'store': 'Coppel'
    },
    'homedepot': {
        'patterns': ['homedepot.com.mx'],
        'currency': 'MXN',
        'store': 'Home Depot'
    },
    'elektra': {
        'patterns': ['elektra.com.mx'],
        'currency': 'MXN',
        'store': 'Elektra'
    },
    'costco': {
        'patterns': ['costco.com.mx'],
        'currency': 'MXN',
        'store': 'Costco'
    },
    'sams': {
        'patterns': ['sams.com.mx'],
        'currency': 'MXN',
        'store': "Sam's Club"
    },
    'bestbuy': {
        'patterns': ['bestbuy.com.mx'],
        'currency': 'MXN',
        'store': 'Best Buy'
    },
    'officedepot': {
        'patterns': ['officedepot.com.mx'],
        'currency': 'MXN',
        'store': 'Office Depot'
    },
    'soriana': {
        'patterns': ['soriana.com'],
        'currency': 'MXN',
        'store': 'Soriana'
    },
    'sanborns': {
        'patterns': ['sanborns.com.mx'],
        'currency': 'MXN',
        'store': 'Sanborns'
    },
    'sears': {
        'patterns': ['sears.com.mx'],
        'currency': 'MXN',
        'store': 'Sears'
    },
    'palacio': {
        'patterns': ['elpalaciodehierro.com'],
        'currency': 'MXN',
        'store': 'El Palacio de Hierro'
    },
    'shein': {
        'patterns': ['shein.com.mx', 'shein.com'],
        'currency': 'MXN',
        'store': 'Shein'
    },
    'aliexpress': {
        'patterns': ['aliexpress.com', 'es.aliexpress'],
        'currency': 'USD',
        'store': 'AliExpress'
    },
    'ebay': {
        'patterns': ['ebay.com'],
        'currency': 'USD',
        'store': 'eBay'
    }
}

def detect_platform(url):
    """Detectar la plataforma basada en la URL"""
    url_lower = url.lower()
    
    for platform, config in PLATFORM_CONFIG.items():
        for pattern in config['patterns']:
            if pattern in url_lower:
                return platform, config
    
    # Extraer nombre de tienda del dominio
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        store_name = domain.split('.')[0].capitalize()
    except:
        store_name = 'Tienda Online'
    
    return 'generic', {'currency': 'MXN', 'store': store_name}


# ============================================
# UTILIDADES PARA EXTRACCIÓN DE PRECIOS
# ============================================
def clean_price(price_text):
    """Limpiar y convertir texto de precio a número"""
    if not price_text:
        return 0
    
    # Remover caracteres no numéricos excepto , y .
    clean = re.sub(r'[^\d.,]', '', str(price_text).strip())
    
    if not clean:
        return 0
    
    # Manejar diferentes formatos de precio
    if ',' in clean and '.' in clean:
        if clean.rfind(',') > clean.rfind('.'):
            clean = clean.replace('.', '').replace(',', '.')
        else:
            clean = clean.replace(',', '')
    elif ',' in clean:
        parts = clean.split(',')
        if len(parts) == 2 and len(parts[1]) <= 2:
            clean = clean.replace(',', '.')
        else:
            clean = clean.replace(',', '')
    
    try:
        return float(clean)
    except:
        return 0


def extract_price_from_text(text):
    """Extraer precio de un texto que puede contener símbolos de moneda"""
    if not text:
        return 0
    
    patterns = [
        r'\$\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*(?:MXN|USD|EUR)',
        r'(?:precio|price)[:\s]*([\d,]+\.?\d*)',
        r'([\d]{1,3}(?:,\d{3})*(?:\.\d{2})?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return clean_price(match.group(1))
    
    return clean_price(text)


# ============================================
# EXTRACTOR UNIVERSAL DE DATOS
# ============================================
def universal_extract(driver, url, platform_config):
    """Extractor universal que funciona con cualquier tienda online"""
    print(f"[UNIVERSAL] Extrayendo datos de: {url}")
    
    result = {
        'name': '',
        'price': 0,
        'image': '',
        'currency': platform_config.get('currency', 'MXN'),
        'store': platform_config.get('store', 'Tienda Online')
    }
    
    time.sleep(3)
    
    # ============================================
    # ESTRATEGIA 1: Meta Tags
    # ============================================
    meta_strategies = [
        {'name': 'meta[property="og:title"]', 'attr': 'content'},
        {'name': 'meta[property="og:image"]', 'attr': 'content', 'field': 'image'},
        {'name': 'meta[property="product:price:amount"]', 'attr': 'content', 'field': 'price'},
        {'name': 'meta[property="og:price:amount"]', 'attr': 'content', 'field': 'price'},
        {'name': 'meta[itemprop="price"]', 'attr': 'content', 'field': 'price'},
        {'name': 'meta[name="twitter:title"]', 'attr': 'content'},
        {'name': 'meta[name="twitter:image"]', 'attr': 'content', 'field': 'image'},
        {'name': 'meta[name="title"]', 'attr': 'content'},
    ]
    
    for strategy in meta_strategies:
        try:
            element = driver.find_element(By.CSS_SELECTOR, strategy['name'])
            value = element.get_attribute(strategy['attr'])
            
            if value:
                field = strategy.get('field', 'name')
                if field == 'price':
                    price = clean_price(value)
                    if price > 0:
                        result['price'] = price
                elif field == 'image' and not result['image']:
                    result['image'] = value
                elif field == 'name' and not result['name']:
                    result['name'] = value.strip()
        except:
            pass
    
    # ============================================
    # ESTRATEGIA 2: JSON-LD (Schema.org)
    # ============================================
    try:
        scripts = driver.find_elements(By.CSS_SELECTOR, 'script[type="application/ld+json"]')
        for script in scripts:
            try:
                data = json.loads(script.get_attribute('innerHTML'))
                if isinstance(data, list):
                    for item in data:
                        extract_from_jsonld(item, result)
                else:
                    extract_from_jsonld(data, result)
            except:
                pass
    except:
        pass
    
    # ============================================
    # ESTRATEGIA 3: Selectores CSS comunes
    # ============================================
    
    # Selectores de NOMBRE
    name_selectors = [
        'h1.product-title', 'h1.product-name', 'h1.pdp-title',
        'h1[class*="title"]', 'h1[class*="name"]', 'h1[class*="product"]',
        '.product-title h1', '.product-name h1',
        '#productTitle', '#product-title', '#title',
        '[data-testid="product-title"]',
        '.ui-pdp-title', '.product__title',
        'h1'
    ]
    
    if not result['name']:
        for selector in name_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                if element and element.text.strip():
                    result['name'] = element.text.strip()
                    break
            except:
                pass
    
    # Selectores de PRECIO
    price_selectors = [
        '.price-current', '.current-price', '.final-price', '.sale-price',
        '.price--current', '.price-value', '.product-price',
        '[data-testid="price"]', '[data-price]',
        '.price', '.precio', '.product__price', '.pdp-price',
        '#priceblock_ourprice', '#priceblock_dealprice',
        '.a-price .a-offscreen', '.a-price-whole',
        '.andes-money-amount__fraction', '.price-tag-fraction',
        '.product-price__price', '.price-info__price',
        '[class*="price"]', '[class*="precio"]',
        'span[class*="price"]', 'div[class*="price"]'
    ]
    
    if result['price'] == 0:
        for selector in price_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip() or element.get_attribute('content') or element.get_attribute('data-price')
                    if text:
                        price = extract_price_from_text(text)
                        if price > 0:
                            result['price'] = price
                            break
                if result['price'] > 0:
                    break
            except:
                pass
    
    # Selectores de IMAGEN
    image_selectors = [
        '.product-image img', '.pdp-image img', '.gallery-image img',
        '#landingImage', '#imgBlkFront', '#main-image',
        '.ui-pdp-image', '.ui-pdp-gallery__figure img',
        '[data-testid="product-image"]', '[data-zoom]',
        '.product__photo img', '.primary-image',
        'img[class*="product"]', 'img[class*="gallery"]'
    ]
    
    if not result['image']:
        for selector in image_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                img_url = (element.get_attribute('src') or 
                          element.get_attribute('data-src') or 
                          element.get_attribute('data-zoom'))
                if img_url and img_url.startswith('http'):
                    result['image'] = img_url
                    break
            except:
                pass
    
    # ============================================
    # ESTRATEGIA 4: Buscar en el HTML/JavaScript
    # ============================================
    if result['price'] == 0:
        try:
            page_source = driver.page_source
            price_patterns = [
                r'"price"\s*:\s*"?([\d,.]+)"?',
                r'"salePrice"\s*:\s*"?([\d,.]+)"?',
                r'"currentPrice"\s*:\s*"?([\d,.]+)"?',
                r'"offerPrice"\s*:\s*"?([\d,.]+)"?',
                r'"finalPrice"\s*:\s*"?([\d,.]+)"?',
                r'data-price="([\d,.]+)"',
            ]
            
            for pattern in price_patterns:
                match = re.search(pattern, page_source)
                if match:
                    price = clean_price(match.group(1))
                    if price > 0 and price < 10000000:
                        result['price'] = price
                        break
        except:
            pass
    
    # ============================================
    # LIMPIEZA FINAL
    # ============================================
    if result['name']:
        unwanted = [
            '| MercadoLibre', '- MercadoLibre', '| Amazon', '- Amazon',
            '| Liverpool', '- Liverpool', '| Walmart', '- Walmart',
            '✓ Compra online de manera segura con Compra Protegida ©',
            '❤', '✓', '©'
        ]
        for text in unwanted:
            result['name'] = result['name'].replace(text, '')
        result['name'] = result['name'].strip()
    
    if not result['name']:
        try:
            result['name'] = driver.title.split('|')[0].split('-')[0].strip()
        except:
            result['name'] = 'Producto'
    
    print(f"[UNIVERSAL] Resultado: {result['name'][:50]}... | ${result['price']} | Imagen: {'✓' if result['image'] else '✗'}")
    return result


def extract_from_jsonld(data, result):
    """Extraer datos de Schema.org JSON-LD"""
    if not isinstance(data, dict):
        return
    
    item_type = data.get('@type', '')
    
    if item_type in ['Product', 'IndividualProduct', 'ProductModel']:
        if not result['name'] and data.get('name'):
            result['name'] = data['name']
        
        if not result['image'] and data.get('image'):
            img = data['image']
            if isinstance(img, list):
                result['image'] = img[0] if img else ''
            elif isinstance(img, dict):
                result['image'] = img.get('url', '')
            else:
                result['image'] = img
        
        offers = data.get('offers', {})
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        
        if result['price'] == 0:
            price = offers.get('price') or offers.get('lowPrice') or data.get('price')
            if price:
                result['price'] = clean_price(str(price))
    
    if '@graph' in data:
        for item in data['@graph']:
            extract_from_jsonld(item, result)


# ============================================
# SCRAPERS ESPECÍFICOS POR PLATAFORMA
# ============================================

def scrape_mercadolibre(driver, url):
    """Scraping optimizado para MercadoLibre"""
    print(f"[ML] Scraping: {url}")
    
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    config = {'currency': 'MXN', 'store': 'MercadoLibre'}
    result = universal_extract(driver, url, config)
    
    if result['price'] == 0:
        try:
            price_el = driver.find_element(By.CSS_SELECTOR, '.andes-money-amount__fraction')
            if price_el:
                result['price'] = clean_price(price_el.text)
        except:
            pass
    
    return result


def scrape_amazon(driver, url):
    """Scraping optimizado para Amazon"""
    print(f"[AMZ] Scraping: {url}")
    
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    
    try:
        if 'captcha' in driver.page_source.lower():
            return {'error': 'CAPTCHA_DETECTADO', 'message': 'Amazon requiere verificación CAPTCHA'}
    except:
        pass
    
    config = {'currency': 'MXN', 'store': 'Amazon'}
    result = universal_extract(driver, url, config)
    
    if result['price'] == 0:
        amazon_price_selectors = [
            '#corePrice_feature_div .a-offscreen',
            '.a-price .a-offscreen',
            '#priceblock_ourprice',
            '#priceblock_dealprice',
            '.a-price-whole',
            '#price_inside_buybox',
            '#newBuyBoxPrice',
            'span[data-a-color="price"] .a-offscreen'
        ]
        
        for selector in amazon_price_selectors:
            try:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                text = element.text.strip() or element.get_attribute('textContent')
                if text:
                    price = extract_price_from_text(text)
                    if price > 0:
                        result['price'] = price
                        break
            except:
                pass
    
    if not result['name'] or len(result['name']) < 5:
        try:
            title = driver.find_element(By.ID, 'productTitle')
            if title:
                result['name'] = title.text.strip()
        except:
            pass
    
    return result


def scrape_generic(driver, url, platform_config):
    """Scraping genérico para cualquier tienda"""
    print(f"[GEN] Scraping: {url}")
    
    driver.get(url)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)
    
    return universal_extract(driver, url, platform_config)


# ============================================
# DEBUG: CAPTURA DE PANTALLA
# ============================================
def take_screenshot(driver, url):
    """Tomar captura de pantalla para debug"""
    print(f"[DEBUG] Tomando screenshot de: {url}")
    
    driver.get(url)
    time.sleep(3)
    
    screenshot = driver.get_screenshot_as_base64()
    
    debug_info = {
        'title': driver.title,
        'url': driver.current_url,
    }
    
    try:
        h1 = driver.find_element(By.TAG_NAME, 'h1')
        debug_info['h1'] = h1.text[:100] if h1.text else 'No h1 text'
    except:
        debug_info['h1'] = 'No h1 found'
    
    try:
        price_el = driver.find_element(By.CSS_SELECTOR, '[class*="price"]')
        debug_info['price_element'] = price_el.text[:50] if price_el.text else 'No price text'
    except:
        debug_info['price_element'] = 'No price found'
    
    meta_info = {}
    for prop in ['og:title', 'og:image', 'og:price:amount', 'product:price:amount']:
        try:
            el = driver.find_element(By.CSS_SELECTOR, f'meta[property="{prop}"]')
            meta_info[prop] = el.get_attribute('content')
        except:
            pass
    debug_info['meta_tags'] = meta_info
    
    return {
        'screenshot': f'data:image/png;base64,{screenshot}',
        'debug': debug_info
    }


# ============================================
# ENDPOINTS
# ============================================
@app.route('/', methods=['GET'])
def home():
    """Endpoint de health check"""
    return jsonify({
        'status': 'ok',
        'service': 'Universal Product Scraper API (Python + Selenium)',
        'version': '2.0.0',
        'supported_stores': list(PLATFORM_CONFIG.keys()) + ['cualquier tienda online'],
        'endpoints': {
            'POST /api/scrape': 'Scrape product from any URL',
            'POST /scrape': 'Alias for /api/scrape',
            'POST /api/debug': 'Get screenshot and debug info',
            'POST /debug': 'Alias for /api/debug'
        }
    })


# Endpoint principal y alias para compatibilidad
@app.route('/scrape', methods=['POST', 'OPTIONS'])
@app.route('/api/scrape', methods=['POST', 'OPTIONS'])
def scrape():
    """Endpoint principal de scraping"""
    if request.method == 'OPTIONS':
        return '', 200
    
    data = request.get_json() or {}
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL es requerida'}), 400
    
    print(f"\n{'='*60}")
    print(f"[SCRAPE] URL: {url}")
    print(f"{'='*60}")
    
    driver = None
    try:
        driver = get_chrome_driver(headless=True)
        platform, config = detect_platform(url)
        print(f"[SCRAPE] Plataforma: {platform} | Tienda: {config['store']}")
        
        if platform == 'mercadolibre':
            result = scrape_mercadolibre(driver, url)
        elif platform == 'amazon':
            result = scrape_amazon(driver, url)
        else:
            result = scrape_generic(driver, url, config)
        
        driver.quit()
        
        if 'error' in result:
            return jsonify({'success': False, **result})
        
        return jsonify({
            'success': True,
            'data': {
                'url': url,
                'platform': platform,
                **result,
                'scrapedAt': datetime.now(timezone.utc).isoformat()
            }
        })
    
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        traceback.print_exc()
        if driver:
            driver.quit()
        
        return jsonify({
            'success': False,
            'error': 'ERROR_SCRAPING',
            'message': str(e)
        }), 500


@app.route('/debug', methods=['POST'])
@app.route('/api/debug', methods=['POST'])
def debug():
    """Endpoint de debug con screenshot"""
    data = request.get_json() or {}
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL es requerida'}), 400
    
    driver = None
    try:
        driver = get_chrome_driver(headless=True)
        result = take_screenshot(driver, url)
        driver.quit()
        return jsonify({'success': True, **result})
    except Exception as e:
        if driver:
            driver.quit()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# MAIN
# ============================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Universal Product Scraper API v2.0")
    print("="*60)
    print("Tiendas soportadas:")
    for platform, config in PLATFORM_CONFIG.items():
        print(f"  • {config['store']}")
    print("  • + Cualquier tienda online (extracción universal)")
    print("="*60)
    print("Endpoints:")
    print("  POST /scrape  - Extraer datos de producto")
    print("  POST /debug   - Captura de pantalla para debug")
    print("="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
