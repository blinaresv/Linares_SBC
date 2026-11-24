"""Pruebas del servicio biométrico sin red: se simulan las respuestas del servicio."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

import servicio_biometrico as sb
from base_conocimiento import REGLAS, CONCLUSIONES
from casos import BASE
from motor_inferencia import encadenamiento_adelante, obtener_conclusiones

CONFIG = {c: "x" for c in sb.CAMPOS_CONFIG}

RESP_VALIDACION_OK = {
    "faceRiskDetected": False, "spoofDetected": False, "esValido": True, "resultado": "OK",
    "score": 92.4, "intentos": 1, "spoofPrediction": None,
    "respuestaTransaccion": {"isHomologacion": False, "esExitosa": True, "errorEntransaccion": None},
}


def decision(hechos):
    finales, _ = encadenamiento_adelante(REGLAS, hechos)
    c = obtener_conclusiones(finales, CONCLUSIONES)
    return c[0]["hecho"] if c else None


def test_validacion_exitosa_se_aprueba():
    hechos, _ = sb.mapear_validacion(RESP_VALIDACION_OK, BASE)
    assert hechos["score_facial"] == 92
    assert decision(hechos) == "aprobado"


def test_alerta_de_riesgo_rechaza_por_fraude():
    resp = dict(RESP_VALIDACION_OK, faceRiskDetected=True)
    hechos, _ = sb.mapear_validacion(resp, BASE)
    assert hechos["en_lista_riesgo"] is True
    assert decision(hechos) == "rechazo_fraude"


def test_suplantacion_rechaza_por_fraude():
    resp = {"spoofDetected": True, "score": 0.0, "respuestaTransaccion": {
        "esExitosa": False, "errorEntransaccion": [{"codigo": "115", "descripcion": "No es persona real"}]}}
    hechos, _ = sb.mapear_validacion(resp, BASE)
    assert decision(hechos) == "rechazo_fraude"


def test_sin_rostro_es_captura_invalida():
    resp = {"respuestaTransaccion": {"esExitosa": False, "errorEntransaccion": [{"codigo": "116"}]}}
    hechos, _ = sb.mapear_validacion(resp, BASE)
    assert decision(hechos) == "captura_invalida"


def test_error_desconocido_no_genera_hechos():
    resp = {"respuestaTransaccion": {"esExitosa": False,
                                     "errorEntransaccion": [{"codigo": "105", "descripcion": "Sin transacciones"}]}}
    hechos, notas = sb.mapear_validacion(resp, BASE)
    assert hechos is None and "105" in notas[0]


def test_falta_configuracion():
    with pytest.raises(sb.ErrorServicio):
        sb.ServicioBiometrico({})


def test_flujo_completo_simulado(monkeypatch):
    llamadas = []

    class Resp:
        def __init__(self, datos):
            self.datos, self.status_code = datos, 200

        def json(self):
            return self.datos

    def falso_post(url, json, headers, timeout, verify):
        llamadas.append(url)
        if url == "token":
            return Resp({"accessToken": "abc", "expiresIn": 1800})
        assert headers["Authorization"] == "Bearer abc"
        if url == "proceso":
            return Resp({"data": {"esExitosa": True, "estadoProceso": 2,
                                  "guidCiudadano": "c1", "procesoConvenioGuid": "p1"}})
        return Resp(RESP_VALIDACION_OK)

    monkeypatch.setattr(sb.requests, "post", falso_post)
    config = dict(CONFIG, url_token="token", url_proceso="proceso", url_validar="validar")
    servicio = sb.ServicioBiometrico(config)
    estado, ciu, proc = servicio.crear_proceso("CC", "123")
    assert (estado, ciu, proc) == (2, "c1", "p1")
    resp = servicio.validar_biometria(ciu, proc, sb.imagen_a_base64(b"img"), "image/jpeg")
    assert resp["esValido"] is True
    assert llamadas == ["token", "proceso", "validar"]   # el token se pide una sola vez


def test_documento_exitoso():
    resp = {"anvExitoso": True, "revExitoso": True,
            "datos": {"data": {"nombreCompleto": "RAMIREZ TORRES CARLOS"}},
            "respuestaTransaccion": {"esExitosa": True, "errorEntransaccion": []}}
    ok, notas = sb.mapear_documento(resp)
    assert ok and "RAMIREZ TORRES CARLOS" in notas[0]


def test_documento_con_cara_rechazada():
    resp = {"anvExitoso": True, "revExitoso": False, "revMensaje": "Reverso borroso",
            "respuestaTransaccion": {"esExitosa": False,
                                     "errorEntransaccion": [{"codigo": "120", "descripcion": "Documento no válido"}]}}
    ok, notas = sb.mapear_documento(resp)
    assert not ok and any("Reverso borroso" in n for n in notas)


def test_enrolamiento_envia_selfie_y_documento(monkeypatch):
    cuerpos = {}

    class Resp:
        status_code = 200

        def __init__(self, datos):
            self.datos = datos

        def json(self):
            return self.datos

    def falso_post(url, json, headers, timeout, verify):
        cuerpos[url] = json
        if url == "token":
            return Resp({"accessToken": "abc", "expiresIn": 1800})
        return Resp({"respuestaTransaccion": {"esExitosa": True, "errorEntransaccion": []}})

    monkeypatch.setattr(sb.requests, "post", falso_post)
    servicio = sb.ServicioBiometrico(dict(CONFIG, url_token="token", url_guardar="guardar",
                                          url_documento="documento", guid_conv="conv"))
    servicio.guardar_biometria("c1", "selfie", "image/jpeg")
    servicio.guardar_documento("c1", "p1", "anv", "image/jpeg", "rev", "image/png", "CC")
    doc = cuerpos["documento"]
    assert doc["GuidConv"] == "conv" and doc["GuidProcesoConvenio"] == "p1" and doc["GuidCiu"] == "c1"
    assert doc["Anverso"] == {"Valor": "anv", "Formato": "image/jpeg"}
    assert doc["Reverso"] == {"Valor": "rev", "Formato": "image/png"}
    assert doc["DatosAdi"] == "CC"
