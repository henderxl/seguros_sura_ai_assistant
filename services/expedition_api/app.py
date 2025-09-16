# app.py
from flask import Flask, request, jsonify
import random
import json
from pathlib import Path
from datetime import datetime

app = Flask(__name__)

REQUIRED_FIELDS = [
    "identificacion_tomador",
    "celular_tomador",
    "marca_vehiculo",
    "modelo_vehiculo",
    "linea_vehiculo",
    "clase_vehiculo",
    "color_vehiculo",
    "plan_poliza",
    "valor_total_poliza",
    "valor_mensual",
]

POLIZAS_DIR = Path(__file__).parent / "polizas"
POLIZAS_DIR.mkdir(parents=True, exist_ok=True)

@app.route("/expedir-poliza", methods=["POST"])
def expedir_poliza():
    if not request.is_json:
        return jsonify({"error": "El cuerpo debe ser JSON"}), 400

    data = request.get_json(silent=True) or {}

    # Validaciones básicas
    missing = [f for f in REQUIRED_FIELDS if f not in data]
    non_string = [f for f in REQUIRED_FIELDS if f in data and not isinstance(data[f], str)]

    if missing or non_string:
        return jsonify({
            "error": "Datos inválidos",
            "faltantes": missing,
            "no_texto": non_string
        }), 400

    # Generar número aleatorio de 10 cifras (con ceros a la izquierda si aplica)
    numero_poliza = str(random.randint(0, 9_999_999_999)).zfill(10)

    # Construir payload a guardar
    payload = {
        **{k: data[k] for k in REQUIRED_FIELDS},
        "numero_poliza": numero_poliza,
        "fecha_emision": datetime.utcnow().isoformat() + "Z"
    }

    # Guardar archivo en polizas/{numero}.json
    outfile = POLIZAS_DIR / f"{numero_poliza}.json"
    try:
        with outfile.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        return jsonify({
            "error": "No se pudo guardar la póliza en disco",
            "detalle": str(e)
        }), 500

    return jsonify({
        "numero_poliza": numero_poliza,
        "archivo": str(outfile.relative_to(Path(__file__).parent)),
        "mensaje": "Póliza emitida y guardada correctamente."
    }), 201


if __name__ == "__main__":
    app.run(host="localhost", port=8000, debug=True)
