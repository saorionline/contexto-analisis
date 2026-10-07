"""
Simulador · Trisectorial Estacional
===================================
Genera los datos crudos (raw) de 4 sectores × 4 seasons (oct-2025 → sep-2026):

    src/<carpeta>/<catalogo>_raw.csv                 catálogo de entidades (10 por sector)
    src/<carpeta>/seasonN_campana_<sector>_raw.csv   13 semanas de datos por season (S01–S13)

- Mismos índices en todos los sectores; cambia el tipo de conversión y la curva de demanda.
- Solo se escriben datos que se capturan: los KPIs (CTR, CPA, ROAS, ROI…) los calcula el pipeline.
- Se siembran errores a propósito; el detalle queda en src/simulacion/anomalias_sembradas.csv.
- Cada archivo generado se anota en src/registro_tamano.csv (filas, disco, memoria, segundos).

Es reproducible: la misma SEMILLA produce exactamente los mismos archivos.
Uso:  python src/simulacion/simulador.py
"""
import csv
import datetime as dt
import random
import time
from pathlib import Path

try:
    import pandas as pd                                      # opcional: solo para medir memoria
except ImportError:
    pd = None

SEMILLA = 20251001
SRC = Path(__file__).resolve().parents[1]
rng = random.Random(SEMILLA)

# ---------------------------------------------------------------------------
# Calendario: 4 seasons de 3 meses, 13 semanas de datos cada una (la S13 absorbe los días sobrantes)
# ---------------------------------------------------------------------------
SEASONS = {
    1: (dt.date(2025, 10, 1), dt.date(2025, 12, 31)),
    2: (dt.date(2026, 1, 1), dt.date(2026, 3, 31)),
    3: (dt.date(2026, 4, 1), dt.date(2026, 6, 30)),
    4: (dt.date(2026, 7, 1), dt.date(2026, 9, 30)),
}


def semanas_de(season):
    inicio, fin = SEASONS[season]
    for n in range(1, 14):
        f_ini = inicio + dt.timedelta(days=7 * (n - 1))
        f_fin = fin if n == 13 else f_ini + dt.timedelta(days=6)
        yield f"S{n:02d}", f_ini, f_fin


# ---------------------------------------------------------------------------
# Geografía compartida: mismas 5 ciudades y 2 países en todos los sectores
# ---------------------------------------------------------------------------
PAIS = {"Miami": "USA", "Nueva York": "USA", "Houston": "USA", "Orlando": "USA", "Bogotá": "Colombia"}
ZONAS = ["Centro", "Norte", "Sur", "Oriente", "Poniente"]

# ---------------------------------------------------------------------------
# Curvas de demanda por sector (peso por mes) + ajustes por país + eventos puntuales
# ---------------------------------------------------------------------------
CURVAS = {
    "resto": {  # similar al café: Navidad, Día de la Madre, Amor y Amistad
        "mes": {10: 1.00, 11: 1.15, 12: 1.40, 1: 0.75, 2: 0.90, 3: 0.95,
                4: 1.00, 5: 1.20, 6: 1.05, 7: 0.95, 8: 0.95, 9: 1.10},
        "pais": {},
        "eventos": {"USA": {(2025, 10, 31): 1.4, (2026, 2, 8): 1.8, (2026, 2, 14): 2.0, (2026, 5, 10): 1.9},
                    "Colombia": {(2026, 2, 14): 1.5, (2026, 5, 10): 2.0, (2026, 9, 19): 2.0}},
        "rangos": [((2025, 12, 18), (2025, 12, 31), 1.4)],
    },
    "retail": {  # Black Friday y Navidad; regreso a clases según el país
        "mes": {10: 1.00, 11: 1.60, 12: 1.80, 1: 0.80, 2: 0.75, 3: 0.85,
                4: 0.90, 5: 1.00, 6: 0.95, 7: 1.00, 8: 1.15, 9: 0.95},
        "pais": {"Colombia": {1: 1.00, 2: 0.95, 8: 0.95}},  # en Colombia el regreso a clases es en enero
        "eventos": {"USA": {(2025, 11, 28): 3.0, (2025, 12, 1): 2.2},
                    "Colombia": {(2025, 11, 28): 2.4, (2025, 12, 1): 1.6, (2026, 9, 19): 1.5}},
        "rangos": [((2025, 12, 15), (2025, 12, 24), 1.6)],
    },
    "fitness": {  # propósitos de año nuevo y pre-verano (más fuerte en USA)
        "mes": {10: 0.90, 11: 0.75, 12: 0.60, 1: 1.80, 2: 1.40, 3: 1.15,
                4: 1.15, 5: 1.30, 6: 1.10, 7: 0.85, 8: 0.90, 9: 1.00},
        "pais": {"Colombia": {5: 1.05, 6: 0.95, 7: 0.90}},  # sin verano marcado
        "eventos": {"USA": {}, "Colombia": {}},
        "rangos": [((2026, 1, 1), (2026, 1, 15), 1.3)],
    },
    "tech": {  # cierre de año fiscal y regreso a clases
        "mes": {10: 1.00, 11: 1.10, 12: 1.45, 1: 0.80, 2: 0.95, 3: 1.10,
                4: 0.95, 5: 1.00, 6: 1.15, 7: 0.85, 8: 1.30, 9: 1.20},
        "pais": {"Colombia": {1: 1.15, 2: 1.10, 8: 1.00}},
        "eventos": {"USA": {(2025, 11, 28): 1.6, (2025, 12, 1): 1.8},
                    "Colombia": {(2025, 11, 28): 1.3, (2025, 12, 1): 1.4}},
        "rangos": [],
    },
}


def peso_dia(sector, pais, d):
    c = CURVAS[sector]
    p = c["pais"].get(pais, {}).get(d.month, c["mes"][d.month])
    p *= c["eventos"][pais].get((d.year, d.month, d.day), 1.0)
    for ini, fin, f in c["rangos"]:
        if dt.date(*ini) <= d <= dt.date(*fin):
            p *= f
    return p


def intensidad(sector, pais, f_ini, f_fin):
    """Demanda media de la semana de datos (1.0 = semana normal)."""
    dias = [(f_ini + dt.timedelta(n)) for n in range((f_fin - f_ini).days + 1)]
    return sum(peso_dia(sector, pais, d) for d in dias) / len(dias)


# ---------------------------------------------------------------------------
# Entidades
# (id, nombre, zona, categoria, ciudad, tipo_conversion)
# ---------------------------------------------------------------------------
FITNESS = [
    ("F001", "Pulso Gym", "Centro", "Gimnasio", "Miami", "membresía mensual"),
    ("F002", "Núcleo Funcional", "Norte", "Crossfit", "Nueva York", "membresía mensual"),
    ("F003", "Andes Training", "Norte", "Entrenamiento personal", "Bogotá", "plan de sesiones"),
    ("F004", "Raíz Yoga Studio", "Poniente", "Yoga y Pilates", "Houston", "membresía mensual"),
    ("F005", "Marea Fit", "Sur", "Contenido fitness", "Miami", "suscripción a programa online"),
    ("F006", "Ritmo Box", "Oriente", "Boxeo fitness", "Orlando", "membresía mensual"),
    ("F007", "Cumbre Pilates", "Centro", "Yoga y Pilates", "Bogotá", "membresía mensual"),
    ("F008", "Hierro 24", "Centro", "Gimnasio", "Nueva York", "membresía mensual"),
    ("F009", "Vatio Cycling", "Sur", "Ciclismo indoor", "Houston", "paquete de clases"),
    ("F010", "Coach Alma", "Norte", "Entrenamiento personal", "Miami", "suscripción a programa online"),
]
RETAIL = [
    ("C001", "Precio Justo Market", "Centro", "Supermercado económico", "Miami", "compra en línea"),
    ("C002", "Todo a Cinco", "Norte", "Tienda de descuento", "Nueva York", "compra en línea"),
    ("C003", "Bodega Ahorro", "Sur", "Hogar y cocina", "Bogotá", "compra en línea"),
    ("C004", "Moda Flash", "Poniente", "Ropa económica", "Houston", "compra en línea"),
    ("C005", "Canasta Express", "Oriente", "Supermercado económico", "Miami", "compra en línea"),
    ("C006", "Casa Fácil Outlet", "Centro", "Hogar y cocina", "Orlando", "compra en línea"),
    ("C007", "Paso Firme Outlet", "Norte", "Calzado", "Bogotá", "compra en línea"),
    ("C008", "Ahorra Kids", "Sur", "Juguetería", "Nueva York", "compra en línea"),
    ("C009", "Belleza al Costo", "Centro", "Cosmética", "Houston", "compra en línea"),
    ("C010", "Enchufe Barato", "Poniente", "Accesorios electrónicos", "Miami", "compra en línea"),
]
TECH = [
    ("T001", "Nubeflow", "Centro", "SaaS de gestión", "Miami", "demo agendada"),
    ("T002", "Cifra Segura", "Norte", "Ciberseguridad", "Nueva York", "demo agendada"),
    ("T003", "Andina Devices", "Norte", "Dispositivos", "Bogotá", "solicitud de cotización"),
    ("T004", "Lumen Analytics", "Poniente", "SaaS de datos", "Houston", "demo agendada"),
    ("T005", "Pixel Hogar", "Sur", "Hogar inteligente", "Miami", "solicitud de cotización"),
    ("T006", "AulaBit", "Oriente", "EdTech", "Orlando", "registro a prueba gratuita"),
    ("T007", "Kódigo Pyme", "Centro", "Software contable", "Bogotá", "registro a prueba gratuita"),
    ("T008", "Vector Wear", "Sur", "Wearables", "Nueva York", "solicitud de cotización"),
    ("T009", "Orbe Cloud", "Centro", "Infraestructura cloud", "Houston", "demo agendada"),
    ("T010", "Tándem CRM", "Norte", "SaaS de ventas", "Miami", "demo agendada"),
]
TIPO_CONV_RESTO = {"Japonesa": "pedido a domicilio", "Vietnamita": "reserva de mesa", "Mariscos": "reserva de mesa",
                   "Heladería": "cupón canjeado en local", "Cervecería": "reserva de mesa",
                   "Bar y Repostería": "reserva de mesa", "Sándwiches": "pedido a domicilio",
                   "Deli": "pedido a domicilio", "Bar": "reserva de mesa"}

# Rangos de parámetros base por sector (por semana normal)
PARAMS = {
    "retail":  dict(inv=(3000, 8000), cpm=(14, 26), ctr=(0.015, 0.030), cr=(0.045, 0.085),
                    ticket=(22, 65), cv=(0.55, 0.70)),
    "fitness": dict(inv=(1500, 4000), cpm=(35, 70), ctr=(0.008, 0.018), cr=(0.012, 0.040),
                    ticket=(39, 129), cv=(0.25, 0.40), retencion=(4, 14)),
    "tech":    dict(inv=(4000, 12000), cpm=(60, 120), ctr=(0.005, 0.012), lead=(0.05, 0.12),
                    calif=(0.25, 0.45), cierre=(0.10, 0.25), ticket=(800, 5000), cv=(0.15, 0.35)),
}


def handle(nombre):
    t = nombre.lower()
    for a, b in zip("áéíóúñ", "aeioun"):
        t = t.replace(a, b)
    return "".join(ch for ch in t if ch.isalnum())


# ---------------------------------------------------------------------------
# Parámetros por entidad
# ---------------------------------------------------------------------------
# Parámetros base de los 10 restaurantes, calculados una sola vez a partir del archivo original
# (campana_sprints_raw.csv, 4 semanas de datos de oct-2026, commit 283fb0d). Quedan fijos para que la
# simulación sea reproducible aunque season1_campana_resto_raw.csv se regenere.
RESTO_BASE = {
    "R001": dict(ciudad="Miami", inv=2248.82, cpm=57.83, alcance=0.6491, ctr=0.0221, cr=0.0537, ticket=321.21, cv=0.39),
    "R002": dict(ciudad="Nueva York", inv=2851.66, cpm=52.40, alcance=0.6878, ctr=0.0152, cr=0.0597, ticket=264.62, cv=0.41),
    "R003": dict(ciudad="Bogotá", inv=2357.18, cpm=68.28, alcance=0.6546, ctr=0.0134, cr=0.0352, ticket=474.13, cv=0.33),
    "R004": dict(ciudad="Houston", inv=2105.14, cpm=66.75, alcance=0.6706, ctr=0.0171, cr=0.0710, ticket=312.74, cv=0.37),
    "R005": dict(ciudad="Miami", inv=2027.59, cpm=72.71, alcance=0.6642, ctr=0.0214, cr=0.0343, ticket=110.52, cv=0.44),
    "R006": dict(ciudad="Orlando", inv=2438.76, cpm=56.69, alcance=0.6221, ctr=0.0196, cr=0.0362, ticket=339.12, cv=0.40),
    "R007": dict(ciudad="Bogotá", inv=3200.37, cpm=69.13, alcance=0.6786, ctr=0.0112, cr=0.0363, ticket=275.22, cv=0.34),
    "R008": dict(ciudad="Nueva York", inv=2077.57, cpm=50.33, alcance=0.6472, ctr=0.0141, cr=0.0681, ticket=175.36, cv=0.40),
    "R009": dict(ciudad="Houston", inv=2647.48, cpm=72.49, alcance=0.6534, ctr=0.0168, cr=0.0273, ticket=246.14, cv=0.38),
    "R010": dict(ciudad="Miami", inv=3433.55, cpm=48.19, alcance=0.6424, ctr=0.0188, cr=0.0732, ticket=399.61, cv=0.37),
}
RESTO_CATEGORIA = {"R001": "Japonesa", "R002": "Japonesa", "R003": "Mariscos", "R004": "Vietnamita",
                   "R005": "Heladería", "R006": "Cervecería", "R007": "Bar y Repostería",
                   "R008": "Sándwiches", "R009": "Deli", "R010": "Bar"}


def entidades_resto():
    """Los 10 restaurantes de restaurantes_raw.csv con sus parámetros originales."""
    return [dict(id=rid, tipo_conv=TIPO_CONV_RESTO[RESTO_CATEGORIA[rid]],
                 tendencia=rng.uniform(-0.10, 0.20), **p)
            for rid, p in RESTO_BASE.items()]


def entidades_nuevas(sector, lista):
    p = PARAMS[sector]
    u = lambda k: rng.uniform(*p[k])
    ents = []
    for eid, _, _, _, ciudad, tipo in lista:
        e = dict(id=eid, ciudad=ciudad, tipo_conv=tipo, inv=round(u("inv"), -2), cpm=u("cpm"),
                 alcance=rng.uniform(0.55, 0.75), ctr=u("ctr"), ticket=u("ticket"), cv=round(u("cv"), 2),
                 tendencia=rng.uniform(-0.15, 0.25))
        if sector == "tech":
            e.update(lead=u("lead"), calif=u("calif"), cierre=u("cierre"))
        else:
            e["cr"] = u("cr")
        if sector == "fitness":
            e["retencion"] = u("retencion")
        ents.append(e)
    return ents


# ---------------------------------------------------------------------------
# Generación de las filas de campaña (52 semanas de datos continuas, luego se parten por season)
# La columna se llama `sprint` en los crudos, pero su valor es la semana de datos (S01–S13).
# ---------------------------------------------------------------------------
BASE_COLS = ["id_entidad", "sector", "sprint", "fecha_inicio", "fecha_fin", "ciudad", "pais",
             "tipo_conversion", "inversion_pauta", "impresiones", "alcance", "clics", "conversiones",
             "ticket_promedio", "costo_variable_pct"]
EXTRA_COLS = {"fitness": ["meses_retencion_promedio"], "tech": ["leads", "leads_calificados"]}


def generar_campana(sector, ents):
    por_season = {s: [] for s in SEASONS}
    for e in ents:
        pais = PAIS[e["ciudad"]]
        k = 0
        for season in SEASONS:
            for sprint, f_ini, f_fin in semanas_de(season):
                k += 1
                dias = (f_fin - f_ini).days + 1
                i = intensidad(sector, pais, f_ini, f_fin)
                tend = 1 + e["tendencia"] * k / 52           # mejora o deterioro a lo largo del año
                ruido = lambda a=0.08: rng.uniform(1 - a, 1 + a)

                inv = e["inv"] * dias / 7 * (1 + 0.5 * (i - 1)) * ruido()   # se invierte más en picos
                cpm = e["cpm"] * (1 + 0.3 * (i - 1)) * ruido(0.05)          # y la puja encarece el CPM
                imp = int(inv / cpm * 1000)
                alc = int(imp * min(0.95, e["alcance"] * ruido(0.06)))
                clics = int(imp * e["ctr"] * (1 + 0.4 * (i - 1)) * tend * ruido())

                fila = dict(id_entidad=e["id"], sector=sector, sprint=sprint,
                            fecha_inicio=f_ini.isoformat(), fecha_fin=f_fin.isoformat(),
                            ciudad=e["ciudad"], pais=pais, tipo_conversion=e["tipo_conv"],
                            inversion_pauta=f"{inv:.2f}", impresiones=imp, alcance=alc, clics=clics,
                            costo_variable_pct=f"{e['cv']:.2f}")

                if sector == "tech":
                    leads = int(clics * e["lead"] * i ** 0.6 * tend * ruido(0.12))
                    calif = int(leads * e["calif"] * ruido(0.10))
                    clientes = int(calif * e["cierre"] * ruido(0.20))     # puede ser 0: ciclo largo
                    fila.update(leads=leads, leads_calificados=calif, conversiones=clientes)
                    ticket = e["ticket"] * ruido(0.10)
                else:
                    fila["conversiones"] = max(1, int(clics * e["cr"] * i ** 0.8 * tend * ruido(0.12)))
                    if sector == "retail":                    # en picos hay descuento: ticket más bajo
                        ticket = e["ticket"] * (1 - 0.15 * (i - 1)) * ruido(0.06)
                    else:
                        ticket = e["ticket"] * (1 + 0.05 * (i - 1)) * ruido(0.06)
                if sector == "fitness":                       # quien entra por propósito de año nuevo dura menos
                    ret = e["retencion"] * max(0.6, 1 - 0.3 * (i - 1)) * ruido(0.08)
                    fila["meses_retencion_promedio"] = f"{ret:.1f}"
                fila["ticket_promedio"] = f"{ticket:.2f}"
                por_season[season].append(fila)
    for filas in por_season.values():
        filas.sort(key=lambda f: (f["sprint"], f["id_entidad"]))   # foto por semana de datos, como se captura
    return por_season


# ---------------------------------------------------------------------------
# Siembra de errores (deterministas) + bitácora de lo sembrado
# ---------------------------------------------------------------------------
ANOMALIAS = []


def anotar(archivo, fila, columna, tipo, antes, despues):
    ANOMALIAS.append(dict(archivo=archivo, fila_csv=fila, columna=columna, tipo=tipo,
                          valor_original=antes, valor_sembrado=despues))


def fila_de(filas, obj):
    """Número de línea en el CSV (1 = encabezado) de un dict concreto dentro de la lista final."""
    return next(i for i, f in enumerate(filas) if f is obj) + 2


def ensuciar_campana(archivo, filas, cols, season):
    """Cada season recibe una mezcla distinta de errores típicos de captura."""
    filas = [dict(f) for f in filas]
    pasos = [
        ("espacios", lambda f: ("ciudad", f["ciudad"], f" {f['ciudad']}")),
        ("espacios", lambda f: ("sector", f["sector"], f"{f['sector']}  ")),
        ("mayúsculas/tildes", lambda f: ("ciudad", f["ciudad"],
                                          rng.choice([f["ciudad"].upper(), f["ciudad"].lower().replace("á", "a")]))),
        ("nulo", lambda f: ("clics", f["clics"], "")),
        ("nulo", lambda f: ("alcance", f["alcance"], "")),
        ("formato de fecha", lambda f: ("fecha_inicio", f["fecha_inicio"],
                                         dt.date.fromisoformat(f["fecha_inicio"]).strftime("%d/%m/%Y"))),
        ("coma decimal", lambda f: ("ticket_promedio", f["ticket_promedio"], f["ticket_promedio"].replace(".", ","))),
        ("id con otro formato", lambda f: ("id_entidad", f["id_entidad"], f["id_entidad"].lower())),
        ("incoherencia lógica", lambda f: ("clics", f["clics"], str(int(f["impresiones"]) + rng.randint(10, 500)))),
        ("valor atípico", lambda f: ("inversion_pauta", f["inversion_pauta"], f"{float(f['inversion_pauta']) * 10:.2f}")),
    ]
    # season 1 y 3 reciben 7 tipos; 2 y 4 reciben 8 (mezcla distinta en cada una)
    rng_local = random.Random(SEMILLA + season)
    elegidos = rng_local.sample(pasos, 7 if season % 2 else 8)
    destino = rng.sample(filas, len(elegidos) + 1)          # filas distintas; la última se duplica
    cambios = []
    for (tipo, f_cambio), f in zip(elegidos, destino):
        col, antes, despues = f_cambio(f)
        f[col] = despues
        cambios.append((f, col, tipo, antes, despues))

    # duplicado exacto (justo después de la original) y registro vacío
    original = destino[-1]
    copia = dict(original)
    filas.insert(filas.index(original) + 1, copia)
    vacia = {c: "" for c in cols}
    filas.insert(rng.randrange(len(filas)), vacia)

    # las posiciones se anotan al final, cuando ya no se insertan más filas
    for f, col, tipo, antes, despues in cambios:
        anotar(archivo, fila_de(filas, f), col, tipo, antes, despues)
    anotar(archivo, fila_de(filas, copia), "(fila completa)", "duplicado exacto",
           f"copia de la fila {fila_de(filas, original)}", "")
    anotar(archivo, fila_de(filas, vacia), "(fila completa)", "registro vacío", "", "")
    return filas


def ensuciar_catalogo(archivo, filas, cols):
    """Mismo patrón que restaurantes_raw.csv: espacios, nulos, duplicados y un registro vacío."""
    f = [dict(x) for x in filas]
    cambios = []
    for i, col, nuevo in [(0, "nombre", "  " + f[0]["nombre"]), (2, "zona", f[2]["zona"] + " "),
                          (3, "categoria", " " + f[3]["categoria"])]:
        cambios.append((f[i], col, "espacios", f[i][col], nuevo))
        f[i][col] = nuevo
    for i, col in [(5, "engagement_rate"), (6, "seguidores_instagram"), (8, "engagement_rate")]:
        cambios.append((f[i], col, "nulo", f[i][col], ""))
        f[i][col] = ""
    copia = dict(f[1])
    copia_ws = dict(f[4]); copia_ws["nombre"] += "  "
    vacia = {c: "" for c in cols}
    final = f[:2] + [copia] + f[2:6] + [vacia] + f[6:9] + [copia_ws] + f[9:]
    for obj, col, tipo, antes, despues in cambios:
        anotar(archivo, fila_de(final, obj), col, tipo, antes, despues)
    anotar(archivo, fila_de(final, copia), "(fila completa)", "duplicado exacto", f"copia de la fila {fila_de(final, f[1])}", "")
    anotar(archivo, fila_de(final, vacia), "(fila completa)", "registro vacío", "", "")
    anotar(archivo, fila_de(final, copia_ws), "(fila completa)", "duplicado con espacios",
           f"copia de la fila {fila_de(final, f[4])}", copia_ws["nombre"])
    return final


# ---------------------------------------------------------------------------
# Escritura + contador de tamaño
# ---------------------------------------------------------------------------
REGISTRO = SRC / "registro_tamano.csv"
REG_COLS = ["fecha_registro", "etapa", "sector", "season", "archivo", "filas", "bytes_disco", "bytes_memoria", "segundos"]


def bytes_en_memoria(ruta):
    if pd is None:
        return ""                                            # sin pandas no se mide la memoria
    return int(pd.read_csv(ruta, dtype=str).memory_usage(deep=True).sum())


def escribir(ruta, cols, filas, sector, season, t0):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(filas)
    nuevo = not REGISTRO.exists()
    with open(REGISTRO, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REG_COLS)
        if nuevo:
            w.writeheader()
        w.writerow(dict(fecha_registro=dt.datetime.now().isoformat(timespec="seconds"), etapa="simulacion",
                        sector=sector, season=season, archivo=ruta.relative_to(SRC).as_posix(), filas=len(filas),
                        bytes_disco=ruta.stat().st_size, bytes_memoria=bytes_en_memoria(ruta),
                        segundos=f"{time.perf_counter() - t0:.4f}"))


def escribir_md(ruta_csv, titulo):
    """Copia idéntica en Markdown (1 espacio de relleno por celda; celda vacía = nulo)."""
    with open(ruta_csv, encoding="utf-8", newline="") as f:
        filas = list(csv.reader(f))
    lineas = [f"# {titulo}", "", f"Copia idéntica de `{ruta_csv.name}`. Datos **simulados** con errores sembrados.", "",
              "<!-- Formato: cada celda lleva exactamente 1 espacio de relleno a cada lado. "
              "Los espacios extra son parte del dato (anomalía intencional). Celda vacía = valor nulo. -->", "",
              "| " + " | ".join(filas[0]) + " |", "|" + "|".join(["---"] * len(filas[0])) + "|"]
    lineas += ["| " + " | ".join(r) + " |" for r in filas[1:]]
    ruta_csv.with_suffix(".md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


CARPETA = {"resto": "rts-csv", "fitness": "ftnss-csv", "retail": "rtl-csv", "tech": "tech-csv"}
CATALOGO = {"fitness": ("fitness_raw.csv", FITNESS), "retail": ("retail_raw.csv", RETAIL), "tech": ("tech_raw.csv", TECH)}
CAT_COLS = ["id_entidad", "nombre", "zona", "categoria", "seguidores_instagram", "engagement_rate", "url_instagram"]


def main():
    if REGISTRO.exists():
        REGISTRO.unlink()                                    # cada simulación parte de un registro limpio
    for sector in ["resto", "fitness", "retail", "tech"]:
        carpeta = SRC / CARPETA[sector]
        if sector == "resto":
            ents = entidades_resto()                         # su catálogo ya existe (restaurantes_raw.csv)
        else:
            t0 = time.perf_counter()
            nombre_cat, lista = CATALOGO[sector]
            cat = [dict(id_entidad=eid, nombre=nom, zona=zona, categoria=catg,
                        seguidores_instagram=rng.randrange(10_000, 50_001, 50),
                        engagement_rate=f"{rng.uniform(1.2, 6.0):.1f}",
                        url_instagram=f"https://www.instagram.com/{handle(nom)}/")
                   for eid, nom, zona, catg, _, _ in lista]
            cat = ensuciar_catalogo(f"{CARPETA[sector]}/{nombre_cat}", cat, CAT_COLS)
            escribir(carpeta / nombre_cat, CAT_COLS, cat, sector, "", t0)
            ents = entidades_nuevas(sector, lista)

        cols = BASE_COLS + EXTRA_COLS.get(sector, [])
        for season, filas in generar_campana(sector, ents).items():
            t0 = time.perf_counter()
            nombre = f"season{season}_campana_{sector}_raw.csv"
            filas = ensuciar_campana(f"{CARPETA[sector]}/{nombre}", filas, cols, season)
            escribir(carpeta / nombre, cols, filas, sector, season, t0)
            if sector == "resto":
                escribir_md(carpeta / nombre, f"Season {season} · Campaña restaurantes (raw)")

    with open(SRC / "simulacion" / "anomalias_sembradas.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ANOMALIAS[0]))
        w.writeheader()
        w.writerows(ANOMALIAS)
    print(f"✅ Simulación lista · {len(ANOMALIAS)} anomalías sembradas · registro en {REGISTRO.name}")


if __name__ == "__main__":
    main()
