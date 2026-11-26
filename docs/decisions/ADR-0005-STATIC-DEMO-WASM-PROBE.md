# ADR 0005 · Demo estática y prueba WASM

**Estado**. La aplicación local A sigue operativa. La demo B está
implementada y verificada localmente. La publicación queda pendiente de
acceso autorizado a Vercel. C permanece experimental.

## Modalidad B

`frontend/demo` es un consumidor independiente de `@nextgenai/ui`. El
banner «DEMO MODE — SYNTHETIC DATA» permanece visible al desplazarse.
El consumidor ofrece filtros y evidencias expandibles y descarga tres
reportes prefabricados. No acepta archivos. La CSP niega conexiones.
El contenido proviene de un fixture sintético procesado de forma estática
con el motor y sin ejecutar su código. El directorio de salida solo contiene
la demo. Vercel no necesita funciones, variables secretas ni un API.

Para una revisión local, ejecutá `npm ci`, `npm run build:demo` y
`python -m http.server 8000 --bind 127.0.0.1 --directory frontend/demo/dist`.
Abrí `http://127.0.0.1:8000`. Esto sirve solo el build de la demo.

Para publicar en una cuenta autorizada con uso elegible para Hobby:

1. En Vercel, elegí **Add New → Project** y conectá el repositorio
   `romim127/NEXA-ScriptGuard` en la rama `main`.
2. Usá la raíz del repositorio, preset **Other** y Node.js 24.
   `vercel.json` declara `npm ci`, `npm run build:demo` y
   `frontend/demo/dist`. Revisá que el build tenga solo recursos estáticos.
3. Ejecutá Deploy y verificá la URL que Vercel devuelve. Confirmá el banner
   persistente, filtrado, evidencia y descargas. Verificá que la demo se
   limite a explorar y descargar los fixtures.

[Vercel build configuration](https://vercel.com/docs/builds/configure-a-build) · [Hobby](https://vercel.com/docs/plans/hobby)

## Modalidad C

`frontend/experiments/wasm` abre un Worker local con estos componentes y
compara una muestra por lenguaje con el runtime nativo:

| Componente | Resultado medido en Edge |
|---|---|
| Pyodide 314.0.8 | El motor Python existente produjo PY-001 en ambos runtimes. Carga 2.516 ms, muestra 80 ms, memoria lineal observada 30 MiB. Núcleo WASM 9.597.892 bytes, stdlib 2.545.550 bytes y JS de núcleo 1.250.259 bytes. |
| web-tree-sitter 0.25.10 y Bash 0.25.1 | El árbol sintáctico de una muestra coincidió. Carga y parseo 41 ms. WASM del runtime 205.488 bytes y gramática 1.358.224 bytes. Las reglas y el análisis de flujo aún requieren integrar ese árbol con el adaptador Python. |
| Rust `wasm32-wasip1` | Se compiló el helper existente a 132.154 bytes. El módulo requiere `wasi_snapshot_preview1` para el contrato de proceso, argumentos y stdin. La prueba inspecciona los imports y no ejecuta el helper en el navegador. |

La medición corresponde a una corrida local por loopback con un Worker.
La memoria lineal observada es una fotografía del runtime Python, no su
pico ni una cuota dura. El Worker puede terminarse desde la UI; no es por sí
solo una frontera de red ni un límite de memoria. El objetivo de C requiere
paridad en todo el corpus, redacción y exportación, integración del árbol
Bash, decisión sobre un adaptador Rust, mediciones de pico y una política de
aislamiento que mantenga los archivos en el navegador. Estos experimentos
no se empaquetan ni despliegan con la demo.

### Reproducir

Desde la raíz con dependencias Python y frontend ya instaladas, prepará
Chromium para Playwright y ejecutá:

```text
npm install --prefix .venv/phase5-probe --ignore-scripts pyodide@314.0.8 web-tree-sitter@0.25.10 tree-sitter-bash@0.25.1
rustup target add wasm32-wasip1
cargo build --locked --release --target wasm32-wasip1 --manifest-path rust/nexa-scriptguard-helper/Cargo.toml
node frontend/experiments/wasm/run.mjs
```

`NEXA_PYTHON` selecciona el intérprete y `PLAYWRIGHT_CHANNEL=msedge` usa
Edge instalado. El experimento sirve únicamente sus archivos del mapa
local y usa fuentes sintéticas fijas.

[Pyodide en Workers](https://pyodide.org/en/stable/usage/webworker.html) · [Web Tree-sitter](https://github.com/tree-sitter/tree-sitter/blob/master/lib/binding_web/README.md)
