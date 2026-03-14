# Credit Approval System v2

Sistema de aprobación crediticia con **OCR local + Ollama (LLM local)**.

## Stack

- **FastAPI** + Python 3.12
- **PostgreSQL** 17 + SQLAlchemy 2.0 + Alembic
- **Ollama** — LLM local (`llama3.1:8b` por defecto)
- **pymupdf** — extracción de texto digital
- **Tesseract OCR** — OCR para PDFs escaneados
- **Docker** + Docker Compose

## Inicio local 
# Ollama (Linux/Mac/Windows)
# https://ollama.com/download

# Descarga el modelo
ollama pull llama3.1:8b

# Python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Base de datos
createdb creditdb
# Edita alembic.ini línea 3 con tu usuario de postgres

# Variables de entorno
cp .env.example .env
# → edita DATABASE_URL y OLLAMA_BASE_URL

# Migraciones
alembic upgrade head

# Servidor
uvicorn app.main:app --reload
```

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/applications` | Crear solicitud |
| GET | `/applications` | Listar solicitudes |
| GET | `/applications/{id}` | Consultar estado |
| POST | `/applications/{id}/documents` | Subir comprobante |
| POST | `/applications/{id}/evaluate` | Re-evaluar |
| GET | `/applications/{id}/audit` | Trazabilidad |
| GET | `/scorecredito` | Score de prueba |
| GET | `/dashboard` | Estadísticas |

## Endpoints de diagnóstico IA

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/ai/test` | Verifica conexión con Ollama |
| POST | `/ai/test-ocr` | Prueba solo el OCR local |
| POST | `/ai/test-document` | Flujo completo: OCR + Ollama |
| POST | `/ai/test-address-match` | Compara dos direcciones |

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | URL de Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modelo a usar | `llama3.1:8b` |
| `DATABASE_URL` | URL de PostgreSQL | `postgresql://...` |
| `OCR_MIN_CHARS` | Mínimo de chars para considerar OCR exitoso | `50` |
| `UPLOAD_DIR` | Directorio de documentos subidos | `./uploads` |

## Reglas de negocio (personal_loan)

| Regla | Umbral |
|-------|--------|
| Score crediticio | ≥ 500 |
| Ingreso mensual | ≥ $5,000 MXN |
| Antigüedad bancaria | ≥ 6 meses |
| No en lista negra | — |
| Coincidencia de dirección | ≥ 60% |
| Ratio deuda-ingreso | ≤ 40% |
