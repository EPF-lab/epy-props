# EPY Props NBA

Motor + página para analizar props de jugadores NBA (defensa por posición, continuidad de plantilla, ajuste de rol).
Lee `CLAUDE.md` primero: contiene el contexto completo del proyecto y las tareas pendientes.

    web/index.html            Página (un solo archivo). Ábrela con doble clic.
    sheets/                   Libro con fórmulas vivas (se importa a Google Sheets).
    data/                     Datos limpios y entradas (CSV).
    scripts/fetch_ids.py      IDs de fotos (py fetch_ids.py "archivo.csv").
    scripts/backtest/         Backtest de pretemporada (datos sintéticos de prueba + fetch_data.py real).
    scripts/pipeline_sandbox/ Scripts originales que generaron los datos (ver aviso en CLAUDE.md).
    apps_script/Code.gs       Conecta las hojas con la página en vivo.

Windows: usar `py` en lugar de `python`.
