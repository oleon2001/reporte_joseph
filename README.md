# Reporte de Transacciones Atrapadas EPA (VE, SV y GT)

Sistema automatizado para la extracción, validación en base de datos, consolidación en Excel y envío por correo de los reportes diarios de transacciones atrapadas y discrepancias en tiendas Ferretería EPA (Venezuela, El Salvador y Guatemala).

---

## Requisitos Previos del Sistema

1. **Python**: Versión 3.10 o superior (recomendado 3.10 a 3.12).
2. **Java (JRE o JDK)**:
   - Necesario para `JPype1` y `JayDeBeApi` al interactuar con las bases de datos AS400 / DB2.
   - Debe estar en el PATH del sistema (`java -version`).
3. **Driver JDBC AS400 (`jt400.jar`)**:
   - Ya se encuentra incluido en la raíz de este proyecto (`./jt400.jar`).
4. **Driver ODBC de SQL Server** (para conexiones a Stellar):
   - **En Windows**: `{SQL Server}` (incluido por defecto en Windows) o `{ODBC Driver 17 for SQL Server}`.
   - **En Linux**: `{ODBC Driver 17 for SQL Server}` (`msodbcsql17`).
5. **Acceso de Red / VPN**:
   - Conectividad a las IPs y dominios de EPA (Web BIRT, Monitor, tiendas Stellar y servidores centrales AS400).

---

## Instalación y Puesta en Marcha

### Paso 1: Clonar o extraer el proyecto
Si descargó el archivo `.zip` o `.rar`, descomprímalo y abra una terminal en la carpeta del proyecto:
```bash
cd reporte_joseph
```

### Paso 2: Crear y activar entorno virtual (Recomendado)
```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Activar en Windows (CMD):
.\venv\Scripts\activate.bat

# Activar en Linux / macOS:
source venv/bin/activate
```

### Paso 3: Instalar librerías de Python
```bash
pip install -r requirements.txt
```

### Paso 4: Descargar navegador para Playwright
Playwright requiere descargar los binarios de Chromium para la generación de reportes y PDFs:
```bash
playwright install chromium
```

---

## Configuración (.env)

Cree su archivo de configuración local a partir de la plantilla:

```bash
# En Windows (PowerShell):
Copy-Item .env.example .env

# En Windows (CMD):
copy .env.example .env

# En Linux / macOS:
cp .env.example .env
```

Edite el archivo `.env` para especificar sus credenciales:
```env
# Correo emisor para Gmail (si se ejecuta sin interacción o por cron)
GMAIL_USER=tu_correo@gmail.com
GMAIL_APP_PASSWORD=tu_contraseña_de_aplicacion_16_caracteres

# Credenciales de bases de datos (opcionales si se ejecutan en red local con valores por defecto)
STELLAR_STORE_USER=oZkbrCFK
STELLAR_STORE_PASS=...
```

---

## Comandos de Ejecución

### 1. Prueba rápida local (Sin conexión a red ni envío)
Ideal para verificar que todas las dependencias y la generación de archivos funcionan:
```bash
python main.py --mock --dry-run --no-confirm
```

### 2. Ejecución completa en producción
Ejecuta la extracción web real, consultas a BD, genera los PDFs y el consolidado Excel, y solicita confirmación antes de enviar el correo:
```bash
python main.py
```

### 3. Generar reportes sin enviar correo (--dry-run)
Genera todos los PDFs y el archivo Excel en la carpeta `salidas/DD-MM-YYYY/` pero no envía el correo electrónico:
```bash
python main.py --dry-run
```

### 4. Filtrar por países específicos (--only)
Procesar solo determinados países (ej. solo Venezuela y Guatemala):
```bash
python main.py --only VE,GT
```

### 5. Enviar correo de prueba a un solo destinatario
Para pruebas de correo sin enviar a toda la lista de distribución corporativa:
```bash
python main.py --test-recipient mi_usuario@intelix.biz
```

### 6. Ejecutar pruebas unitarias y de conectividad
```bash
python test_local.py
```

---

## Estructura del Repositorio

* **`main.py`**: Punto de entrada del programa. Orquesta la extracción, validación, Excel y envío.
* **`config.py`**: Configuración central (hosts, URLs, selectores web, lista de destinatarios).
* **`web_extractor.py`**: Módulo Playwright para interactuar con Reporte Web (BIRT) y Monitor.
* **`db_validator.py`**: Consultas y validación en bases de datos (SQL Server Stellar y AS400 DB2).
* **`excel_builder.py`**: Construye el archivo Excel consolidado (`Detalles de Tr's atrapadas DD-MM-YYYY.xlsx`).
* **`mailer.py`**: Manejo de conexión SMTP con Gmail y envío de adjuntos.
* **`entregables.py`**: Versionado histórico (`entregables/vX/`).
* **`jt400.jar`**: Driver JDBC para IBM AS400 / DB2.
* **`sql/`**: Directorio de consultas SQL para cada país y origen de datos.
* **`salidas/`**: Carpetas diarias con los 6 PDFs generados y la hoja de cálculo.
* **`tiendas_apagadas.json`**: Registro de tiendas apagadas para excluir de las alertas.

