# Development setup

## Windows PowerShell

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install ".[test]"
python -m nexa_scriptguard.gui
```

The GUI binds only to loopback. Keep the process running while using the
private URL it prints; `Ctrl+C` stops it. The optional helper is built with:

```powershell
cargo build --manifest-path rust\nexa-scriptguard-helper\Cargo.toml
```

## Linux and macOS

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install ".[test]"
python -m nexa_scriptguard.gui
```

CI declares Windows, Ubuntu, and macOS with Python 3.10 and 3.12. This
documentation does not claim that every OS was tested locally.

## Arranque habitual

Después de instalar las dependencias, ejecutá `run-windows.bat` en CMD o
`.\run-windows.bat` en PowerShell. En Bash usá `./run-linux.sh` o
`bash ./run-linux.sh`. Desde otro directorio indicá la ruta completa al
lanzador. Los lanzadores priorizan el `.venv` del repositorio y aceptan un
entorno virtual activo compatible cuando falta ese intérprete. Los argumentos
se reenvían a la GUI. Usá una ruta absoluta para el helper Rust cuando
arranques desde otro directorio.

Mantené la terminal abierta durante el uso. La GUI intenta abrir el navegador
predeterminado y muestra una URL privada para abrirla manualmente si hace
falta. Cada instancia usa un puerto propio en `127.0.0.1` y su propio token.
Presioná Ctrl+C para cerrar. Si CMD pregunta si debe terminar el archivo por
lotes, confirmá el cierre.

## Instalar `RUN` para usarlo desde cualquier directorio

Con pipx instalado, ejecutá `pipx install .` desde la raíz del repositorio.
Usá `pipx environment --value PIPX_BIN_DIR` para consultar la ubicación del
comando. Podés ejecutarlo por ruta absoluta, o elegir `pipx ensurepath` para
agregar el directorio al PATH de tu usuario. Abrí otra terminal después de ese
cambio, verificá con `RUN --help` y ejecutá `RUN` para iniciar. En CMD usá
`where RUN`, en PowerShell `Get-Command RUN`, y en Bash `command -v RUN` si
hay otro programa con ese nombre.

La instalación puede descargar dependencias. El arranque y el análisis
funcionan offline una vez instalado el proyecto. Para actualizar desde el
repositorio, ejecutá `pipx reinstall nexa-scriptguard`. Para retirar el comando,
ejecutá `pipx uninstall nexa-scriptguard`.
[Configuración de PATH de pipx](https://pipx.pypa.io/latest/how-to/configure-paths.html)

## Desarrollo del frontend

Con Node.js 24, desde la raíz, ejecutá `npm ci`, `npm run typecheck`,
`npm run lint`, `npm test` y `npm run build`. El bundle se genera en
`nexa_scriptguard/gui_assets/modern` y se versiona junto con su fuente.
Iniciá Python con el lanzador habitual para probarlo. Las instalaciones con
bundle funcionan sin Node.js ni servidor Vite. Para comparar la GUI anterior,
abrí `/legacy` en la pestaña de sesión o agregá el fragmento privado de la URL
que imprimió el proceso actual.
