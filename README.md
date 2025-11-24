#  Pipeline de Extracción SFTP para Cobranzas - Zenta Solvant

**Empresa:** Zenta  
**Proyecto:** Solvant - Sistema de Cobranzas  
**Estado:** Production Ready 

Pipeline de extracción de datos de cobranza desde archivos TXT de ancho fijo almacenados en SFTP. Procesa información de usuarios en mora, genera CSV normalizado, almacena en Google Cloud Storage y dispara procesamiento posterior en Firestore para activar batch calls del backend.

##  Propósito

Pipeline especializado en **extracción y preparación de datos de cobranza** que:
-  Extrae archivos TXT de formato fijo desde SFTP del cliente
-  Convierte 78 campos de ancho fijo a CSV estructurado  
-  Almacena CSV en Google Cloud Storage para trazabilidad
-  Registra logs de extracción en Firestore
-  Dispara pipeline de transformación (Cloud Run Job) para procesamiento batch

##  Arquitectura del Pipeline

### Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PIPELINE DE EXTRACCIÓN                           │
└─────────────────────────────────────────────────────────────────────┘

1️ EXTRACCIÓN (SFTP)
   │
   ├─ Conexión SFTP → Archivo TXT ancho fijo (78 campos)
   │  └─ Formato estándar del cliente (posiciones fijas)
   │
   └─ Parse línea por línea → RegistroTxtFull (Pydantic)

2️ TRANSFORMACIÓN (CSV)
   │
   ├─ Extracción de 15 campos clave para cobranza
   │  ├─ Identificación: queue, rut, nombre
   │  ├─ Deuda: días_mora, monto_mensual, monto_vencido
   │  ├─ Contacto: email, tarjeta
   │  └─ Fechas: fecha_proceso, fecha_vencimiento
   │
   └─ Generación CSV → output/csv/{id}.csv

3️ CARGA (GCS + Firestore)
   │
   ├─ Upload CSV → Google Cloud Storage
   │  └─ gs://{bucket}/extractions/{fecha}/{id}/{archivo}.csv
   │
   ├─ Registro de logs → Firestore logs_collection
   │  ├─ ID extracción
   │  ├─ Timestamp UTC
   │  ├─ Contadores (extraídos, procesados)
   │  ├─ Status (OK/ERROR)
   │  └─ URL del CSV en GCS
   │
   └─ Trigger → Cloud Run Job (Pipeline Transformación)
      └─ Lee CSV desde GCS
      └─ Carga registros en Firestore data_collection
      └─ Activa Batch Call en Backend
```

### Componentes Principales

####  **Servicios (src/services/)**

| Servicio | Propósito | Tecnología |
|----------|-----------|------------|
| `SFTPService` | Extracción de archivos TXT desde SFTP cliente | Paramiko (sync) |
| `CloudStorageService` | Almacenamiento de CSV en GCS | google-cloud-storage |
| `FirestoreService` | Registro de logs y metadata | google-cloud-firestore |
| `CloudRunService` | Disparo de pipeline de transformación | Cloud Run Jobs API |

####  **Modelos de Datos (src/models/)**

| Modelo | Campos | Uso |
|--------|--------|-----|
| `RegistroTxtFull` | 78 campos de ancho fijo | Parse completo del TXT cliente |
| `MetadataUser` | 15 campos clave | CSV simplificado para procesamiento |
| `LogRecord` | id, status, counts, timestamps, urls | Auditoría y trazabilidad |

####  **Configuración (src/config.py)**

Gestión de configuración con Pydantic Settings:
- `AppConfig`: Configuración general (batch_size, retries, log_level)
- `SFTPConfig`: Credenciales SFTP (host, port, username, password)
- `FirestoreConfig`: Configuración Firestore (project, collection, database)
- `CloudStorageConfig`: Configuración GCS (bucket_name)
- `CloudRunConfig`: Configuración Cloud Run Job (job_name, region)

##  Inicio Rápido

### Prerrequisitos

- Python 3.11+ (recomendado 3.11 o 3.12)
- Acceso SFTP del cliente
- Google Cloud Platform con:
  - Cloud Storage bucket configurado
  - Firestore database activo
  - Cloud Run Job de transformación desplegado
  - Service Account con permisos necesarios

### 1. Instalación

```bash
# Clonar repositorio
git clone <url-repositorio>
cd zenta-solvant-pipe-reading

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

Crear archivo `.env` basado en `.env.example`:

```bash
# Configuración general
PROJECT_ID=tu-proyecto-gcp
FIRESTORE_PROJECT_ID=tu-proyecto-gcp
FIRESTORE_COLLECTION=solvant_data
FIRESTORE_LOGS_COLLECTION=solvant_logs
FIRESTORE_DATABASE=(default)

# Google Cloud Storage
GCS_BUCKET_NAME=tu-proyecto-gcp-csv-files
GCS_PROJECT_ID=tu-proyecto-gcp

# SFTP Cliente
SFTP_HOST=sftp.cliente.com
SFTP_PORT=22
SFTP_USERNAME=usuario
SFTP_PASSWORD=password

# Pipeline
PIPELINE_FILE_URL=/ruta/al/archivo.txt

# Cloud Run Job (transformación)
GCP_REGION=us-central1
GCP_JOB_NAME=solvant-transformation-job
GCP_PROJECT_ID=tu-proyecto-gcp

# Credenciales GCP
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
```

### 3. Ejecución

```bash
# Ejecución local
python -m src.main

# Con Docker
docker build -t solvant-extractor .
docker run --env-file .env solvant-extractor
```

## 📊 Formato del Archivo TXT

### Especificación de Campos de Ancho Fijo

El archivo TXT del cliente sigue un formato de **ancho fijo de 1018 caracteres por línea** con 78 campos:

| Campo | Posición | Ancho | Ejemplo | Descripción |
|-------|----------|-------|---------|-------------|
| queue | 0-4 | 4 | `0001` | Cola de atención |
| rut | 4-13 | 9 | `123456789` | RUT + DV |
| branch | 13-18 | 5 | `00001` | Código sucursal |
| name | 48-128 | 80 | `JUAN PEREZ` | Nombre completo |
| days_overdue | 473-478 | 5 | `00030` | Días de mora |
| monthly_payment | 478-493 | 15 | `000000050000` | Pago mensual |
| total_debt | 493-508 | 15 | `000000150000` | Deuda total |
| email | 822-882 | 60 | `cliente@email.com` | Email de contacto |
| ... | ... | ... | ... | (70 campos más) |

**Nota:** El parser completo está en `src/models/registro_txt_full.py`

### CSV Generado (15 campos clave)

El pipeline extrae solo los campos necesarios para cobranza:

```csv
extraction_id,record_index,queue,queue_id_cyber,rut,name,paternal_surname,maternal_surname,days_overdue,monthly_payment,down_payment_option1,process_date,overdue_date1,overdue_amount1,email,card,expiration_date
```

##  Funcionamiento Detallado del Pipeline

### Método `run()` - Orquestador Principal

El pipeline ejecuta 5 pasos secuenciales con manejo robusto de errores:

#### Paso 1: Extracción desde SFTP

```python
raw_data = self.extract()
```

- Conecta a SFTP usando paramiko (sync)
- Lee archivo TXT desde ruta configurada en `PIPELINE_FILE_URL`
- Parsea cada línea con `RegistroTxtFull.from_line()` (78 campos de ancho fijo)
- Retorna lista de diccionarios con todos los campos
- **Robustez:** Registros inválidos se logean pero no detienen el proceso

#### Paso 2: Conversión a CSV

```python
csv_file_path = await self._convert_to_csv(raw_data, extraction_id)
```

- Extrae solo 15 campos clave con `_extract_specific_fields()`
- Campos seleccionados: queue, rut, nombre, días_mora, email, etc.
- Genera CSV en `output/csv/{extraction_id}.csv`
- Usa pandas para escritura optimizada
- **Robustez:** Validación field-by-field con manejo seguro de índices

#### Paso 3: Carga a Google Cloud Storage

```python
gcs_url = await self._upload_to_gcs(csv_file_path, extraction_id)
```

- Estructura: `gs://{bucket}/extractions/{fecha}/{id}/{archivo}.csv`
- Metadata incluida: extraction_id, source_pipeline, timestamp
- Elimina archivo local después de subir exitosamente
- **Robustez:** Retry automático en fallos de red

#### Paso 4: Registro de Logs en Firestore

```python
await self._save_extraction_log(id, status, extracted_count, ...)
```

- Guarda en `FIRESTORE_LOGS_COLLECTION`
- Campos: id, status, timestamps, contadores, errores, csv_location
- Permite auditoría y trazabilidad completa
- **Robustez:** Log se guarda incluso si hay errores en pasos anteriores

#### Paso 5: Trigger de Pipeline de Transformación

```python
await self._trigger_transformation_pipeline(gcs_url, extraction_id)
```

- Usa Cloud Run Jobs API
- Ejecuta job de transformación asíncronamente
- El job lee el CSV desde GCS y carga en Firestore `data_collection`
- Activa Batch Call en backend para llamadas de cobranza
- **Robustez:** Fallo en trigger no afecta la extracción exitosa

### Manejo de Errores y Limpieza

```python
try:
    # Pipeline completo (pasos 1-5)
except Exception as e:
    self.errors.append(str(e))
    await self._save_extraction_log(..., status="ERROR", ...)
    return False
finally:
    # Limpieza garantizada de conexiones
    self.sftp_service.disconnect()
    self.firestore_service.disconnect()
    await self.gcs_service.disconnect()
    self.cloud_run_service.disconnect()
```

### Características de Robustez Implementadas

 **Validación de datos**: Pydantic valida cada registro extraído  
 **Logging estructurado**: Logs detallados en cada paso con contexto  
 **Manejo de errores granular**: Try/except en operaciones críticas  
 **Limpieza de recursos**: Finally block garantiza cierre de conexiones  
 **Persistencia antes de limpieza**: CSV en GCS antes de eliminar local  
 **Auditoría completa**: Logs en Firestore con metadata y contadores  
 **Desacoplamiento**: Fallo en transformación no afecta extracción

##  Operación y Deployment

### Frecuencia de Ejecución

**Programación:** 3 veces al mes en fechas específicas  
**Método:** Cloud Scheduler → Cloud Run Job

```bash
# Ejemplo: días 1, 15 y 25 de cada mes a las 9 AM (Santiago)
gcloud scheduler jobs create http solvant-extractor-scheduler \
  --schedule="0 9 1,15,25 * *" \
  --uri="https://us-central1-run.googleapis.com/.../jobs/solvant-extractor:run" \
  --http-method=POST \
  --time-zone="America/Santiago" \
  --oauth-service-account-email=service-account@project.iam.gserviceaccount.com
```

### Volumen de Datos

- **Registros por archivo:** Variable según ciclo de cobranza
- **Tamaño CSV típico:** 2-5 MB
- **Tiempo de procesamiento:** 2-5 minutos (dependiente de red SFTP)

### Deployment en Google Cloud

```bash
# Build y deploy automático con Cloud Build
gcloud builds submit --config deploy/google/cloudbuild.yaml

# El cloudbuild.yaml gestiona:
# 1. Instalación de dependencias Python
# 2. Build de imagen Docker multi-stage
# 3. Push a Artifact Registry
# 4. Deploy de Cloud Run Job con todas las env vars
```

### Variables de Entorno (Cloud Run)

Configuradas automáticamente en deploy via `cloudbuild.yaml`:

```yaml
--set-env-vars=SFTP_HOST=${_SFTP_HOST}
--set-env-vars=SFTP_USERNAME=${_SFTP_USERNAME}
--set-env-vars=FIRESTORE_COLLECTION=${_FIRESTORE_COLLECTION}
--set-env-vars=GCS_BUCKET_NAME=${_GCS_BUCKET_NAME}
--set-env-vars=GCP_JOB_NAME=${_GCP_JOB_NAME}
# Ver deploy/google/cloudbuild.yaml para lista completa
```

### Permisos Requeridos

Service Account debe tener:
- `roles/storage.objectAdmin` - Subir CSV a GCS
- `roles/datastore.user` - Escribir logs en Firestore
- `roles/run.developer` - Ejecutar Cloud Run Jobs downstream
- Credenciales SFTP configuradas en variables de entorno

## 🔧 Potenciales Mejoras

### Prioridad Alta - Robustez

1. **Retry Logic en SFTP**
   - **Problema actual:** Fallo de conexión SFTP detiene todo el pipeline
   - **Mejora:** Implementar retry con backoff exponencial en `SFTPService.connect()`
   - **Impacto:** Mayor resiliencia ante fallos de red transitorios

2. **Validación de Archivo Antes de Procesar**
   - **Problema actual:** No valida estructura/tamaño del archivo antes de parsear
   - **Mejora:** Validar header, número de líneas esperado, tamaño mínimo/máximo
   - **Impacto:** Detección temprana de archivos corruptos o incorrectos

3. **Idempotencia del Pipeline**
   - **Problema actual:** Re-ejecutar pipeline puede duplicar datos
   - **Mejora:** Check en Firestore si extraction_id ya existe antes de procesar
   - **Impacto:** Permite re-ejecuciones seguras sin duplicados

4. **Circuit Breaker para GCS**
   - **Problema actual:** Fallos repetidos en GCS pueden causar timeout
   - **Mejora:** Implementar patrón circuit breaker con fallback local
   - **Impacto:** Mejor manejo de indisponibilidad temporal de GCS

### Prioridad Media - Mantenibilidad

5. **Tests Unitarios y de Integración**
   - **Problema actual:** No hay tests (directorio `tests/` pero vacío)
   - **Mejora:** Implementar tests con pytest y mocks de servicios externos
   - **Impacto:** Mayor confianza en cambios, detección temprana de bugs

6. **Separación de Configuración por Ambiente**
   - **Problema actual:** Configuración mezclada en .env
   - **Mejora:** Archivos `.env.dev`, `.env.staging`, `.env.prod` separados
   - **Impacto:** Menor riesgo de errores en deploys

7. **Logging de Métricas de Performance**
   - **Problema actual:** Logs básicos sin métricas de tiempo/recursos
   - **Mejora:** Agregar timing decorators y métricas de memory usage
   - **Impacto:** Mejor observabilidad y detección de bottlenecks

8. **Documentación de Campos del TXT**
   - **Problema actual:** Posiciones hardcodeadas en código sin documentación
   - **Mejora:** Archivo de configuración JSON/YAML con especificación de campos
   - **Impacto:** Más fácil adaptar a cambios en formato del cliente

### Prioridad Baja - Optimización

9. **Procesamiento Asíncrono del Parse**
   - **Problema actual:** Parse línea por línea es síncrono
   - **Mejora:** Usar asyncio.gather para parsear en paralelo por chunks
   - **Impacto:** Reducción de tiempo de procesamiento en archivos grandes

10. **Compresión de CSV antes de GCS**
    - **Problema actual:** CSV se sube sin comprimir
    - **Mejora:** Gzip del CSV antes de subir
    - **Impacto:** Reducción de costos de storage y ancho de banda

11. **Dead Letter Queue para Registros Inválidos**
    - **Problema actual:** Registros inválidos solo se logean
    - **Mejora:** Guardar registros inválidos en colección separada para revisión
    - **Impacto:** Auditoría completa y posibilidad de reprocesar

12. **Alertas Proactivas**
    - **Problema actual:** Solo logs, sin notificaciones
    - **Mejora:** Integración con Cloud Monitoring/Alerting
    - **Impacto:** Respuesta más rápida ante fallos

##  Testing (Pendiente)

### Estado Actual
 **No hay tests implementados actualmente**

### Tests Recomendados

```bash
tests/
├── test_pipeline.py          # Tests del flujo completo
│   ├── test_extract_sftp_success
│   ├── test_extract_sftp_connection_error
│   ├── test_convert_to_csv
│   ├── test_upload_to_gcs
│   └── test_full_pipeline_run
├── test_services/
│   ├── test_sftp_service.py
│   ├── test_gcs_service.py
│   ├── test_firestore_service.py
│   └── test_cloudrun_service.py
└── test_models/
    ├── test_registro_txt_full.py
    └── test_metadata_user.py
```

### Ejecutar Tests (cuando se implementen)

```bash
# Todos los tests
python -m pytest

# Con cobertura
python -m pytest --cov=src --cov-report=html

# Tests específicos
python -m pytest tests/test_pipeline.py -v
```

## 🔧 Personalización del Template

### 1. Modificar Modelos de Datos

```python
# src/models/data_models.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MiModeloPersonalizado(BaseModel):
    """Modelo específico para mi caso de uso."""
    
    id: int = Field(..., description="ID único")
    nombre: str = Field(..., min_length=1, max_length=255)
    precio: Optional[float] = Field(None, ge=0)
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Validadores personalizados
    @field_validator('nombre')
    @classmethod
    def validar_nombre(cls, v):
        if not v.strip():
            raise ValueError('El nombre no puede estar vacío')
        return v.strip().title()
```

### 2. Añadir Nuevos Servicios

```python
# src/services/mi_nuevo_servicio.py
from .base_service import BaseService
from typing import List, Dict, Any

class MiNuevoServicio(BaseService):
    """Conector para mi fuente de datos específica."""
    
    async def connect(self) -> bool:
        """Implementar conexión específica."""
        try:
            # Tu lógica de conexión
            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Error conectando: {e}")
            return False
    
    async def extract(self, query: str) -> List[Dict[str, Any]]:
        """Extraer datos de tu fuente."""
        # Tu lógica de extracción
        pass
    
    async def load(self, data: List[Dict[str, Any]]) -> bool:
        """Cargar datos a tu destino."""
        # Tu lógica de carga
        pass
```

### 3. Personalizar Lógica del Pipeline

```python
# src/pipeline.py - Modificar métodos según tu caso de uso

async def extract(self) -> List[Dict[str, Any]]:
    """Personalizar extracción según tu fuente."""
    try:
        # Ejemplo: múltiples fuentes
        query = """
        SELECT id, nombre, precio, categoria, fecha_creacion
        FROM mi_tabla_especifica
        WHERE fecha_creacion >= CURRENT_DATE - INTERVAL '1 day'
        ORDER BY fecha_creacion DESC
        """
        
        data = await self.postgres_service.extract(query)
        logger.info(f"Extraídos {len(data)} registros de mi_tabla_especifica")
        return data
        
    except Exception as e:
        logger.error(f"Error en extracción personalizada: {e}")
        return []

async def transform(self, raw_data: List[Dict[str, Any]]) -> List[MiModeloPersonalizado]:
    """Transformación específica para tu caso de uso."""
    transformed_data = []
    
    for row in raw_data:
        try:
            # Aplicar transformaciones específicas
            row['precio'] = row.get('precio', 0) * 1.21  # Agregar IVA
            row['categoria'] = row.get('categoria', '').upper()
            
            # Validar con tu modelo
            record = MiModeloPersonalizado(**row)
            transformed_data.append(record)
            
        except Exception as e:
            logger.warning(f"Error transformando registro: {e}")
    
    return transformed_data
```

##  Deployment

### Google Cloud Run

```bash
# Usar script automático
./scripts/deploy.sh

# O manual paso a paso
gcloud builds submit --config cloudbuild.yaml .

# Deployment directo con Docker
docker build -t mi-pipeline .
docker tag mi-pipeline gcr.io/mi-proyecto/mi-pipeline
docker push gcr.io/mi-proyecto/mi-pipeline

gcloud run jobs create mi-pipeline-job \
    --image gcr.io/mi-proyecto/mi-pipeline \
    --region us-central1 \
    --set-env-vars LOG_LEVEL=INFO
```

### Variables de Entorno en Cloud Run

```bash
# Configurar secrets para credenciales sensibles
gcloud secrets create postgres-password --data-file=- <<< "tu-password"

# Configurar variables en el job
gcloud run jobs update mi-pipeline-job \
    --set-env-vars LOG_LEVEL=INFO,ENVIRONMENT=production \
    --set-secrets POSTGRES_PASSWORD=postgres-password:latest
```

### Configuración de CI/CD

El archivo `cloudbuild.yaml` incluye:
-  **Build automatizado**: Construcción de imagen Docker
-  **Tests en pipeline**: Ejecución automática de tests
-  **Deploy condicional**: Deployment solo si tests pasan
-  **Versionado**: Tags automáticos por commit

##  Monitoreo y Observabilidad

### Logging Estructurado

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Logs con contexto
logger.info("Iniciando procesamiento", extra={
    "batch_size": 1000,
    "source": "postgresql",
    "destination": "bigquery"
})

# Métricas automáticas
logger.info(f"Procesados {len(data)} registros en {duration:.2f} segundos")
```

### Métricas Incluidas

- ** Tiempos de ejecución**: Por etapa (extract, transform, load)
- ** Contadores**: Registros procesados, errores, éxitos
- ** Calidad de datos**: Porcentaje de validación exitosa
- ** Recursos**: Uso de memoria y conexiones

##  Mejores Prácticas Incluidas

### Seguridad
-  **Variables de entorno** para credenciales
-  **Google Secrets Manager** integration
-  **No hardcoding** de passwords
-  **Logging seguro** (sin exponer credenciales)

### Performance
-  **Async/await** para operaciones I/O
-  **Pool de conexiones** para PostgreSQL
-  **Procesamiento por lotes** configurable
-  **Gestión de memoria** eficiente

### Mantenibilidad
-  **Type hints** completos en Python
-  **Docstrings** en español
-  **Separación de responsabilidades**
-  **Configuración centralizada**

### Robustez
-  **Retry logic** con backoff exponencial
-  **Manejo de errores** granular
-  **Validación de datos** automática
-  **Logging de errores** con contexto

##  Troubleshooting

### Errores Comunes

**1. Error de conexión SFTP**
```
Error: [Errno -2] Name or service not known
```
**Solución:**
- Verificar `SFTP_HOST`, `SFTP_PORT` en `.env`
- Validar conectividad de red: `telnet sftp.host.com 22`
- Revisar firewall/VPN si aplica

**2. Error de permisos en GCS**
```
Error: 403 Forbidden - does not have storage.objects.create permission
```
**Solución:**
- Verificar Service Account tiene role `roles/storage.objectAdmin`
- Validar `GOOGLE_APPLICATION_CREDENTIALS` apunta a JSON correcto
- Confirmar bucket existe: `gsutil ls gs://bucket-name`

**3. Error de parsing de línea TXT**
```
ValidationError: 1 validation error for RegistroTxtFull
```
**Solución:**
- Verificar formato del archivo TXT (1018 caracteres por línea)
- Revisar encoding del archivo (debe ser UTF-8)
- Validar estructura en `src/models/registro_txt_full.py`

**4. Error al ejecutar Cloud Run Job**
```
Error: 404 Job not found
```
**Solución:**
- Verificar `GCP_JOB_NAME` y `GCP_REGION` en `.env`
- Confirmar job existe: `gcloud run jobs list --region=us-central1`
- Validar permisos: Service Account necesita `roles/run.developer`

**5. Error de importación**
```bash
#  Incorrecto
python src/main.py

#  Correcto
python -m src.main
```

##  Monitoreo

### Logs en Cloud Run

```bash
# Ver logs del último job execution
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=solvant-extractor" --limit 50

# Logs de errores únicamente
gcloud logging read "resource.type=cloud_run_job AND severity>=ERROR" --limit 20
```

### Métricas Clave a Monitorear

- **Tasa de éxito:** % de ejecuciones con status OK vs ERROR
- **Tiempo de ejecución:** Duración de cada paso del pipeline
- **Registros procesados:** Total extraídos vs registros con error
- **Tamaño de archivos:** CSV generados para detectar anomalías
- **Fallos de conexión:** SFTP, GCS, Firestore timeouts

## 📚 Estructura del Proyecto

```
zenta-solvant-pipe-reading/
├── src/
│   ├── main.py                    # Punto de entrada
│   ├── config.py                  # Configuración con Pydantic
│   ├── pipeline.py                # Lógica principal del pipeline
│   ├── models/
│   │   ├── registro_txt_full.py   # 78 campos del TXT (ancho fijo)
│   │   ├── metadata_user.py       # 15 campos para CSV
│   │   ├── log_records.py         # Modelo de logs
│   │   └── data_models.py         # Modelos auxiliares
│   ├── services/
│   │   ├── base_service.py        # Clase base abstracta
│   │   ├── sftp_service.py        # Extracción SFTP
│   │   ├── gcs_service.py         # Upload a Cloud Storage
│   │   ├── firestore_service.py   # Logs en Firestore
│   │   └── execute_job.py         # Trigger Cloud Run Job
│   └── utils/
│       ├── logger.py              # Sistema de logging
│       └── validators.py          # Validadores custom
├── output/csv/                    # CSV generados (temporal)
├── deploy/google/
│   └── cloudbuild.yaml            # CI/CD para GCP
├── requirements.txt               # Dependencias producción
├── Dockerfile                     # Container multi-stage
├── .env.example                   # Template de configuración
└── README.md                      # Esta documentación
```

##  Licencia

**Desarrollado para:** Zenta - Sistema Solvant de Cobranzas  
**Versión:** 1.0  
**Última actualización:** Noviembre 2025
