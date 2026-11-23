"""
Integración opcional con un servicio biométrico externo.

El servicio recibe una selfie y la compara contra la biometría que ya tiene
registrada de la persona. Si es la primera vez, la guarda (enrolamiento) y en
las siguientes validaciones compara contra ella. Por eso el sistema no
necesita almacenar imágenes: las conserva el servicio.

Flujo:
1. Pedir token.
2. Crear el proceso de la persona. El servicio responde si es enrolamiento
   (no tiene biometría) o validación (ya la tiene).
3a. Enrolamiento: guardar la selfie.
3b. Validación: comparar la selfie contra la biometría registrada.
4. Convertir la respuesta en hechos para el sistema experto (mapear_validacion).

Las direcciones y las credenciales NO van en el código. Se leen de
.streamlit/secrets.toml (local) o de los Secrets de Streamlit Cloud, en la
sección [servicio]. Ver .streamlit/secrets.example.toml.
"""
import base64
import time

import requests

ENROLAMIENTO = 1
VALIDACION = 2

# Códigos de error del servicio que se pueden traducir a hechos del dominio
ERROR_NO_ES_PERSONA_REAL = "115"
ERROR_NO_ES_ROSTRO = "116"

CAMPOS_CONFIG = ["url_token", "url_proceso", "url_guardar", "url_validar",
                 "client_id", "client_secret", "guid_conv", "usuario", "clave"]


class ErrorServicio(Exception):
    """Error al consumir el servicio biométrico."""


class ServicioBiometrico:
    def __init__(self, config, timeout=60):
        faltantes = [c for c in CAMPOS_CONFIG if not config.get(c)]
        if faltantes:
            raise ErrorServicio("Faltan datos de configuración: " + ", ".join(faltantes))
        self.config = config
        self.timeout = timeout
        self.verificar_ssl = config.get("verificar_ssl", True)
        self._token = None
        self._token_vence = 0

    # ------------------------------------------------------------------
    def _post(self, url, cuerpo, con_token=True):
        encabezados = {"Content-Type": "application/json", "Accept": "application/json"}
        if con_token:
            encabezados["Authorization"] = f"Bearer {self.obtener_token()}"
        try:
            r = requests.post(url, json=cuerpo, headers=encabezados,
                              timeout=self.timeout, verify=self.verificar_ssl)
        except requests.RequestException as e:
            raise ErrorServicio(f"No se pudo conectar con el servicio: {e}") from e
        try:
            datos = r.json()
        except ValueError:
            raise ErrorServicio(f"Respuesta no válida del servicio (HTTP {r.status_code}).")
        if isinstance(datos, dict) and "error" in datos and len(datos) == 1:
            raise ErrorServicio(f"Error del servicio: {datos['error']}")
        return r.status_code, datos

    def obtener_token(self):
        """Pide el token y lo reutiliza mientras esté vigente."""
        if self._token and time.time() < self._token_vence:
            return self._token
        _, datos = self._post(self.config["url_token"], {
            "clientId": self.config["client_id"],
            "clientSecret": self.config["client_secret"],
        }, con_token=False)
        token = datos.get("accessToken")
        if not token:
            raise ErrorServicio(f"No se obtuvo token: {datos.get('errorDescription') or datos}")
        self._token = token
        self._token_vence = time.time() + int(datos.get("expiresIn", 1800)) - 60
        return token

    def crear_proceso(self, tipo_doc, num_doc, email="", celular=""):
        """Crea el proceso. Devuelve (estado_proceso, guid_ciudadano, guid_proceso)."""
        codigo, datos = self._post(self.config["url_proceso"], {
            "guidConv": self.config["guid_conv"],
            "tipoValidacion": int(self.config.get("tipo_validacion", 1)),
            "asesor": "",
            "sede": "",
            "tipoDoc": tipo_doc,
            "numDoc": num_doc,
            "email": email,
            "celular": celular,
            "prefCelular": "57",
            "usuario": self.config["usuario"],
            "clave": self.config["clave"],
        })
        data = datos.get("data") or datos.get("Data") or {}
        if not data.get("esExitosa"):
            mensaje = data.get("Mesage") or data.get("errorEntransaccion") or datos
            raise ErrorServicio(f"No se pudo crear el proceso (HTTP {codigo}): {mensaje}")
        return data["estadoProceso"], data["guidCiudadano"], data["procesoConvenioGuid"]

    def guardar_biometria(self, guid_ciudadano, imagen_b64, formato):
        _, datos = self._post(self.config["url_guardar"], {
            "guidCiu": guid_ciudadano,
            "idServicio": 5,
            "subTipo": "Frontal",
            "valor": imagen_b64,
            "formato": formato,
            "usuario": self.config["usuario"],
            "actualizar": False,
        })
        return datos

    def validar_biometria(self, guid_ciudadano, guid_proceso, imagen_b64, formato):
        _, datos = self._post(self.config["url_validar"], {
            "guidCiudadano": guid_ciudadano,
            "guidProcesoConvenio": guid_proceso,
            "idServicio": 5,
            "subTipo": "Frontal",
            "biometria": imagen_b64,
            "formato": formato,
        })
        return datos


# ----------------------------------------------------------------------
# Funciones sin red: se pueden probar con pytest
# ----------------------------------------------------------------------
def imagen_a_base64(contenido):
    """Convierte los bytes de la imagen a Base64 sin el prefijo data:image."""
    return base64.b64encode(contenido).decode("ascii")


def codigos_error(respuesta):
    trans = (respuesta or {}).get("respuestaTransaccion") or {}
    return [str(e.get("codigo")) for e in (trans.get("errorEntransaccion") or [])]


def mensajes_error(respuesta):
    trans = (respuesta or {}).get("respuestaTransaccion") or {}
    return [f"{e.get('codigo')}: {e.get('descripcion')}" for e in (trans.get("errorEntransaccion") or [])]


def mapear_validacion(respuesta, base):
    """
    Convierte la respuesta de la comparación facial en hechos para el sistema experto.
    'base' son los valores del formulario; solo se cambian los que informa el servicio.
    Devuelve (hechos, notas). Si la respuesta no se puede usar, hechos es None.

    Mapeo:
      score                 -> score_facial (comparación contra la biometría registrada)
      spoofDetected         -> sospecha_suplantacion
      spoofDetected / 115   -> prueba_vida_superada = False
      faceRiskDetected      -> en_lista_riesgo (alerta de riesgo del rostro)
      116                   -> rostro_detectado = False
      intentos              -> intentos
    """
    hechos = dict(base)
    notas = []
    trans = respuesta.get("respuestaTransaccion") or {}
    codigos = codigos_error(respuesta)

    if not trans.get("esExitosa"):
        if ERROR_NO_ES_ROSTRO in codigos:
            hechos.update(rostro_detectado=False, score_disponible=False, score_facial=None)
            notas.append("El servicio no encontró un rostro, o encontró más de uno.")
            return hechos, notas
        if ERROR_NO_ES_PERSONA_REAL in codigos or respuesta.get("spoofDetected"):
            hechos.update(rostro_detectado=True, prueba_vida_superada=False, sospecha_suplantacion=True,
                          score_disponible=False, score_facial=None)
            notas.append("El servicio indicó que la imagen no corresponde a una persona real.")
            return hechos, notas
        return None, mensajes_error(respuesta) or ["La transacción no fue exitosa."]

    spoof = bool(respuesta.get("spoofDetected"))
    prediccion = respuesta.get("spoofPrediction")
    hechos.update(
        rostro_detectado=True,
        prueba_vida_superada=not spoof and prediccion in (None, "", "Real"),
        sospecha_suplantacion=spoof,
        en_lista_riesgo=bool(respuesta.get("faceRiskDetected")),
        score_disponible=True,
        score_facial=int(round(float(respuesta.get("score") or 0))),
    )
    intentos = int(respuesta.get("intentos") or 1)
    hechos["intentos"] = min(max(intentos, 1), 5)
    notas.append(f"Score contra la biometría registrada: {respuesta.get('score')}")
    if respuesta.get("faceRiskDetected"):
        notas.append("El servicio marcó una alerta de riesgo sobre el rostro.")
    return hechos, notas


def mapear_enrolamiento(respuesta):
    """Resume la respuesta del enrolamiento. Devuelve (exitoso, notas)."""
    trans = respuesta.get("respuestaTransaccion") or {}
    if not trans.get("esExitosa"):
        return False, mensajes_error(respuesta) or ["No se pudo registrar la selfie."]
    notas = ["La selfie quedó registrada como la biometría de la persona."]
    if respuesta.get("spoofPrediction"):
        notas.append(f"Análisis de vivacidad: {respuesta['spoofPrediction']}")
    return True, notas
