# Calendar Backend - Python Scraper API

API REST para scraping de productos de Amazon construida con Flask y Playwright.

## 🚀 Características

- Scraping de productos de Amazon (precio, título, imágenes, rating)
- CORS configurado para desarrollo
- Manejo de errores robusto
- Headless browser con Playwright
- Rate limiting y anti-detección

## 📋 Requisitos

- Python 3.8+
- pip

## 🔧 Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Instalar navegador de Playwright:
```bash
playwright install chromium
```

3. Configurar variables de entorno (opcional):
```bash
cp .env.example .env
```

## 🏃 Ejecución

```bash
python app.py
```

El servidor estará disponible en `http://localhost:5000`

## 📡 API Endpoints

### POST /scrape

Extrae información de un producto de Amazon.

**Body:**
```json
{
  "url": "https://www.amazon.com.mx/dp/PRODUCTO_ID"
}
```

**Respuesta:**
```json
{
  "url": "https://www.amazon.com.mx/dp/PRODUCTO_ID",
  "title": "Nombre del producto",
  "price": "1,234.56",
  "currency": "MXN",
  "rating": "4.5",
  "image": "https://...",
  "availability": "En stock"
}
```

## 🛠️ Tecnologías

- **Flask**: Framework web
- **Playwright**: Navegador headless para scraping
- **BeautifulSoup4**: Parsing HTML
- **python-dotenv**: Manejo de variables de entorno

## 📝 Notas

- El scraping está optimizado para Amazon México
- Se recomienda usar proxies o rotar user agents en producción
- Respetar los términos de servicio de Amazon
