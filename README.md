# PARES AI RAG - Prototipo y dossier de arquitectura

Este repositorio contiene el ejercicio final del módulo **Arquitecturas con IA**. La solución propuesta permite consultar en lenguaje natural documentación histórica digitalizada de PARES, generar metadatos basados en fechas y hechos, explorar un índice de hechos documentales y obtener respuestas en texto o PDF con trazabilidad hacia las fuentes.

El proyecto incluye dos partes complementarias:

1. Un **dossier de arquitectura** con la explicación funcional, técnica, de seguridad, monitorización, control de modelos y continuidad de servicio.
2. Un **prototipo ejecutable**, que demuestra de forma local el flujo principal de la solución: ingesta de documentos, extracción de hechos, buscador, consulta en lenguaje natural, roles de usuario, trazas y exportación a PDF.

La implementación local no pretende sustituir a una plataforma cloud productiva. Sirve como prueba de concepto para validar el diseño arquitectónico descrito en el dossier.

## Contenido principal

El repositorio contiene una aplicación web basada en FastAPI y un conjunto de documentos de apoyo para la entrega.

```text
.
├── src/pares_ai/              # Código fuente de la aplicación
├── data/samples/              # Documentos históricos de ejemplo
├── docs/                      # Dossier, diagramas y evidencias de funcionamiento
├── scripts/                   # Scripts auxiliares
├── tests/                     # Pruebas básicas del prototipo
├── runtime/                   # Datos generados en ejecución
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

## Contenido de la carpeta `docs`

La carpeta `docs` contiene los materiales esenciales de la entrega:

| Fichero                               | Descripción                                                                                             |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `Dossier de Arquitecturas de IA.docx` | Documento principal de arquitectura. Incluye la explicación funcional y técnica de la solución.         |
| `Diagrama Funcional.png`              | Diagrama de alto nivel del flujo funcional: ingesta, OCR, extracción, indexación, búsqueda y respuesta. |
| `Diagrama Técnico.png`                | Diagrama de arquitectura técnica con los principales componentes de la solución.                        |
| `entrada.png`                         | Captura de la pantalla inicial del prototipo.                                                           |
| `buscador_de_hechos.png`              | Captura del buscador inicial de hechos documentales.                                                    |
| `respuesta_texto.png`                 | Captura de una respuesta generada en formato texto.                                                     |
| `respuesta-pares-ai.pdf`              | Ejemplo de respuesta exportada a PDF desde el prototipo.                                                |
| `403.png`                             | Captura de control de acceso                                                                            |


## Alcance funcional cubierto

El prototipo y el dossier cubren los puntos principales solicitados en el enunciado:

* Almacenamiento de documentos históricos digitalizados.
* Posibilidad de nuevas ingestas documentales.
* Tratamiento de documentos escaneados y extracción de contenido.
* Generación de metadatos basados en fechas, entidades y hechos.
* Creación de un índice con referencias a los documentos fuente.
* Portal web con buscador inicial de hechos.
* Entrada de lenguaje natural para solicitar resúmenes o datos concretos.
* Respuestas en texto y exportación a PDF.
* Roles diferenciados de administrador y usuario.
* Trazabilidad de consultas, acciones relevantes y documentos recuperados.
* Propuesta de arquitectura cloud con seguridad, observabilidad, control de modelos, alta disponibilidad y recuperación ante desastres.

## Qué implementa el prototipo

La aplicación local implementa una versión simplificada de la arquitectura propuesta:

* Backend con **FastAPI**.
* Frontend web servido por el propio backend.
* Autenticación demo con roles `admin` y `user`.
* Carga de documentos de ejemplo.
* Extracción heurística de fechas, entidades y hechos.
* Buscador inicial de hechos.
* Consulta en lenguaje natural mediante un flujo RAG simplificado.
* Respuestas con referencias a documentos fuente.
* Exportación de respuestas a PDF.
* Registro básico de acciones y trazas.
* Endpoints administrativos para ingesta, auditoría y control de modelos.

En producción, los componentes locales se sustituirían por servicios gestionados de almacenamiento, OCR, búsqueda híbrida, embeddings, LLM, observabilidad e identidad corporativa.

## Ejecución rápida con Docker

Requisitos:

* Docker
* Docker Compose

```shell
cp .env.example .env
docker compose up --build
```

Una vez levantado el contenedor, abre el navegador en:

```text
http://localhost:8000
```

## Ejecución local sin Docker

Requisitos:

* Python 3.11 o superior

Desde PowerShell:

```powershell
python -m venv .venv # Activarlo después
pip install -r requirements.txt
$env:PYTHONPATH="src"
uvicorn pares_ai.main:app --reload --host 0.0.0.0 --port 8000
```

Después, abre:

```text
http://localhost:8000
```

## Uso del prototipo

1. Acceder a `http://localhost:8000`.
2. Entrar como `Admin`.
3. Usar la opción de carga de documentos demo.
4. Buscar hechos documentales, por ejemplo con términos como `San Miguel`, `naves` o `1582`.
5. Realizar una consulta en lenguaje natural.
6. Revisar la respuesta generada y las referencias documentales.
7. Descargar la respuesta en PDF.
8. Entrar como `User` para comprobar que el usuario puede consultar, pero no realizar tareas administrativas.

Ejemplo de consulta:

```text
Necesito el nombre de las naves españolas que participaron en las jornadas de la Batalla de San Miguel, indicando capitanes, arqueo, marinería, nave capitana y almiranta.
```

## Endpoints principales

| Endpoint                         | Descripción                                        | Rol             |
| -------------------------------- | -------------------------------------------------- | --------------- |
| `GET /health`                    | Comprueba el estado del servicio.                  | No aplica       |
| `POST /api/auth/demo-login`      | Login demo con rol `admin` o `user`.               | No aplica       |
| `POST /api/admin/ingest/samples` | Carga los documentos de ejemplo.                   | Administrador   |
| `POST /api/admin/documents`      | Permite subir documentos.                          | Administrador   |
| `GET /api/search?q=...`          | Buscador inicial de hechos.                        | Usuario         |
| `GET /api/facts`                 | Listado de hechos indexados.                       | Usuario         |
| `POST /api/query`                | Consulta en lenguaje natural.                      | Usuario         |
| `GET /api/admin/audit`           | Consulta de trazas y auditoría.                    | Administrador   |
| `GET /api/admin/model-control`   | Información de control y calibración de modelos.   | Administrador   |