
import os
import pandas as pd
import unicodedata
from typing import Optional

# === Tasas por plan (ajústalas a tu tarifario real) ===
PLAN_RATES: dict[str, float] = {
    "Plan Basico": 0.025,         # 2.5%
    "Plan Autos Clasico": 0.035,  # 3.5%
    "Plan Autos Global": 0.045,   # 4.5%
}

# ======= Estado interno (cache) =======
_CATALOGO_DF: Optional[pd.DataFrame] = None
_CATALOGO_PATH: Optional[str] = None
_CATALOGO_SHEET: Optional[str | int] = 0
_CATALOGO_COLMAP: Optional[dict] = None
_CATALOGO_MTIME: Optional[float] = None

# ======= Utils =======
def _norm(s: str) -> str:
    """Normaliza texto: quita acentos, colapsa espacios y pone en minúsculas."""
    if s is None:
        return ""
    s = str(s).strip()
    s = " ".join(s.split())
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

def _canonizar_catalogo(df: pd.DataFrame, col_mappings: Optional[dict]) -> pd.DataFrame:
    """
    Estandariza nombres de columnas a: Marca, Modelo, Linea, Clase, Valor
    y agrega columnas *_norm para búsquedas robustas.
    """
    expected = ["Marca", "Modelo", "Linea", "Clase", "Valor"]  # <<< cambio clave

    if col_mappings is None:
        col_mappings = {}

    current_cols_norm = {_norm(c): c for c in df.columns}
    target_map_auto: dict[str, str] = {}
    for target in expected:
        if target in col_mappings:
            target_map_auto[target] = col_mappings[target]
            continue

        key_norm = _norm(target)
        if key_norm in current_cols_norm:
            target_map_auto[target] = current_cols_norm[key_norm]
        else:
            # heurística simple por inclusión del nombre normalizado
            candidates = [c for n, c in current_cols_norm.items() if key_norm in n]
            if candidates:
                target_map_auto[target] = candidates[0]
            else:
                raise KeyError(
                    f"No encontré la columna para '{target}'. "
                    f"Columnas en el Excel: {list(df.columns)}. "
                    f"Usa 'col_mappings' en configurar_fuente_excel(...)."
                )

    work = df.rename(columns={v: k for k, v in target_map_auto.items()}).copy()

    # columnas normalizadas para filtro exacto robusto
    for col in ["Marca", "Modelo", "Linea", "Clase"]:
        work[col + "_norm"] = work[col].apply(_norm)

    # asegurar que 'Valor' sea numérico
    if not pd.api.types.is_numeric_dtype(work["Valor"]):
        work["Valor"] = pd.to_numeric(work["Valor"], errors="coerce")
    if work["Valor"].isna().all():
        raise ValueError("La columna 'Valor' no contiene valores numéricos interpretables.")

    return work

def _cargar_desde_archivo(path: str, sheet: str | int, colmap: Optional[dict]) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet)
    return _canonizar_catalogo(df, colmap)

def _asegurar_catalogo_cargado():
    """
    Carga/recarga el catálogo si no está listo.
    1) Usa lo configurado por configurar_fuente_excel(...)
    2) Si no existe config, intenta variable de entorno VEHICULOS_XLSX
    """
    global _CATALOGO_DF, _CATALOGO_PATH, _CATALOGO_SHEET, _CATALOGO_COLMAP, _CATALOGO_MTIME

    # Si ya está cargado, revisa si el archivo cambió
    if _CATALOGO_DF is not None and _CATALOGO_PATH:
        try:
            mtime = os.path.getmtime(_CATALOGO_PATH)
            if _CATALOGO_MTIME == mtime:
                return  # sin cambios
            # recargar si cambió
            _CATALOGO_DF = _cargar_desde_archivo(_CATALOGO_PATH, _CATALOGO_SHEET, _CATALOGO_COLMAP)
            _CATALOGO_MTIME = mtime
            return
        except FileNotFoundError:
            # si el archivo ya no existe, caemos al fallback de env
            pass

    # Si no hay path configurado, intenta variable de entorno
    if not _CATALOGO_PATH:
        env_path = os.getenv("VEHICULOS_XLSX")
        if env_path:
            if not os.path.isfile(env_path):
                raise FileNotFoundError(f"VEHICULOS_XLSX='{env_path}' no existe.")
            _CATALOGO_PATH = env_path
            _CATALOGO_SHEET = 0
            _CATALOGO_COLMAP = None
        else:
            raise RuntimeError(
                "Catálogo no configurado. Llama primero a configurar_fuente_excel(path, ...) "
                "o define la variable de entorno VEHICULOS_XLSX con la ruta al .xlsx."
            )

    # Cargar por primera vez
    if _CATALOGO_PATH:
        if not os.path.isfile(_CATALOGO_PATH):
            raise FileNotFoundError(f"No encontré el archivo: {_CATALOGO_PATH}")
        _CATALOGO_DF = _cargar_desde_archivo(_CATALOGO_PATH, _CATALOGO_SHEET, _CATALOGO_COLMAP)
        _CATALOGO_MTIME = os.path.getmtime(_CATALOGO_PATH)

def configurar_fuente_excel(
    excel_path: str,
    sheet_name: str | int = 0,
    col_mappings: Optional[dict] = None,
):
    """
    Configura la fuente del catálogo (se cachea internamente).
    Ej.: configurar_fuente_excel('/ruta/carros.xlsx', 0, {'Valor': 'VALOR_258'})
    """
    global _CATALOGO_DF, _CATALOGO_PATH, _CATALOGO_SHEET, _CATALOGO_COLMAP, _CATALOGO_MTIME
    if not os.path.isfile(excel_path):
        raise FileNotFoundError(f"No encontré el archivo: {excel_path}")

    _CATALOGO_PATH = excel_path
    _CATALOGO_SHEET = sheet_name
    _CATALOGO_COLMAP = col_mappings
    _CATALOGO_DF = _cargar_desde_archivo(excel_path, sheet_name, col_mappings)
    _CATALOGO_MTIME = os.path.getmtime(excel_path)

def cotizar_poliza(
    marca: str,
    modelo: str,
    linea: str,
    clase: str,
    color: str,
    plan_rates: dict[str, float] = PLAN_RATES
    ):
    """
    Cotiza una póliza de seguro para un vehículo.

    """

    if color == "ROJO":
        # Aplicar un recargo del 10% para vehículos rojos
        for plan in plan_rates:
            plan_rates[plan] *= 1.1

    _asegurar_catalogo_cargado()
    catalogo = _CATALOGO_DF

    # Filtro exacto por columnas normalizadas
    filt = (
        (catalogo["Marca_norm"]  == _norm(marca)) &
        (catalogo["Modelo_norm"] == _norm(modelo)) &
        (catalogo["Linea_norm"]  == _norm(linea)) &
        (catalogo["Clase_norm"]  == _norm(clase))
    )
    subset = catalogo.loc[filt]

    if subset.empty:
        ejemplos = catalogo[["Marca", "Modelo", "Linea", "Clase"]].head(10).to_dict(orient="records")
        raise ValueError(
            "No encontré coincidencias exactas con las 4 claves dadas.\n"
            f"Entrada: marca='{marca}', modelo='{modelo}', linea='{linea}', clase='{clase}'.\n"
            "Verifica tildes, espacios y nombres. Ejemplos de filas:\n"
            f"{ejemplos}"
        )

    # Si hay múltiples coincidencias, tomamos la primera (puedes cambiar esta regla)
    row = subset.iloc[0]
    valor_vehiculo = float(row["Valor"])

    # Calcular primas
    quotes: dict[str, dict[str, float]] = {}
    for plan, rate in plan_rates.items():
        anual = round(valor_vehiculo * rate, 2)
        mensual = round(anual / 12.0, 2)
        quotes[plan] = {
            "prima_anual": anual,
            "prima_mensual": mensual,
            "tasa_aplicada": rate,
        }


    return quotes


# ======= Ejemplo de uso =======
if __name__ == "__main__":
    # Configura la fuente UNA SOLA VEZ (o usa la variable de entorno VEHICULOS_XLSX)
    configurar_fuente_excel(
        excel_path="data/carros.xlsx",
        sheet_name=0
    )
    # Ejemplo de cotización
    quotes = cotizar_poliza(
        marca="CHEVROLET",
        modelo="2012",
        linea="FAMILY - MT 1500CC 4P AA",
        clase="AUTOMOVIL",
        color="ROJO"
    )
    print(quotes)
