```markdown
# BunkerVault

BunkerVault es un gestor de contraseñas de escritorio local y offline, diseñado bajo el principio de conocimiento cero (*Zero-Knowledge*). Está enfocado en proporcionar una solución ligera, autónoma y criptográficamente segura sin depender de sincronizaciones en la nube, servidores externos ni servicios de telemetría de terceros.

---

## Características principales

* **Criptografía autenticada:** Cifrado simétrico de datos mediante AES-256-GCM, asegurando tanto la confidencialidad como la integridad de la información contra manipulaciones no autorizadas.
* **Derivación de clave robusta:** Implementación de derivación de claves maestras basada en estándares modernos (PBKDF2-HMAC-SHA256 con salt criptográfico y más de 600.000 iteraciones / Argon2id), mitigando ataques de fuerza bruta basados en GPU y diccionarios.
* **Generador criptográfico y métrica de entropía:** Generación de secretos con `secrets` (CSPRNG del sistema operativo) y cálculo dinámico de entropía de Shannon en bits ($E = L \cdot \log_2(R)$) según el conjunto de caracteres seleccionado, permitiendo además la exclusión de caracteres visualmente ambiguos (`0`, `O`, `l`, `1`, `I`).
* **Protección del portapapeles en memoria:** Hilo asíncrono en segundo plano que purga automáticamente el portapapeles del sistema operativo tras 20 segundos de haber copiado una credencial.
* **Persistencia atómica:** Escritura segura a disco mediante archivos temporales y reemplazo atómico, previniendo la corrupción de la base de datos ante cierres forzados o caídas del sistema.

---

## Arquitectura del proyecto

El código está estructurado bajo una estricta separación de responsabilidades:

```text
├── core/
│   ├── crypto.py         # Derivación de claves y cifrado/descifrado AES-256-GCM
│   ├── generator.py      # Generador CSPRNG y algoritmo de cálculo de entropía
│   └── models.py         # Modelos de datos serializables (PasswordEntry, VaultData)
├── storage/
│   └── vault_manager.py  # Gestor de estado en memoria, persistencia y operaciones CRUD
├── ui/
│   ├── dialogs.py        # Modales de gestión de credenciales y panel del generador
│   ├── login_view.py     # Flujo de autenticación y creación de bóveda
│   ├── main_view.py      # Panel principal, visor con toggle y búsqueda reactiva
│   └── theme.py          # Paleta visual en modo oscuro y estilos de interfaz
├── utils/
│   └── clipboard.py      # Manejo seguro y auto-limpieza temporal del portapapeles
├── tests/
│   ├── test_core.py      # Pruebas unitarias de criptografía, entropía y modelos
│   ├── test_ui.py        # Validación de componentes visuales
│   └── test_vault_manager.py # Pruebas de persistencia e integridad de datos
├── main.py               # Punto de entrada y orquestador del ciclo de vida
└── requirements.txt      # Dependencias del proyecto

```

---

## Requisitos del sistema

* Python 3.10 o superior.
* Soporte para Tkinter en el sistema operativo (en distribuciones basadas en Debian/Ubuntu: `sudo apt install python3-tk`).
* Librería `cryptography` (módulo de primitivas criptográficas).

---

## Instalación y ejecución

### 1. Clonar el repositorio y configurar el entorno

```bash
git clone [https://github.com/notinlovv/BunkerVaultGen.git](https://github.com/notinlovv/BunkerVaultGen.git)
cd BunkerVaultGen
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

```

### 2. Ejecutar la aplicación

```bash
python main.py

```

### 3. Ejecutar la suite de pruebas

El proyecto cuenta con cobertura de pruebas automatizadas mediante `pytest`:

```bash
pytest tests/

```

---

## Empaquetado para distribución

Para generar un binario ejecutable local utilizando PyInstaller sin requerir el intérprete de Python en terminal:

```bash
pyinstaller --noconfirm --onedir --windowed \
  --name "BunkerVault" \
  --hidden-import "cryptography" \
  main.py

```

El ejecutable resultante se ubicará en la ruta `dist/BunkerVault/BunkerVault`.

---

## Licencia

Distribuido bajo la licencia MIT. Consulta el archivo `LICENSE` para más información.

```

```
