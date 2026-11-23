"""
Interfaz web del sistema experto de validación de identidad facial.
Ejecutar desde la carpeta del proyecto con:  streamlit run src/app.py
"""
import logging

import pandas as pd
import streamlit as st

from base_conocimiento import CONCLUSIONES, PREDICADOS, REGLAS, HECHOS_DERIVADOS
from casos import BASE, CASOS_PRUEBA
from grafica import grafica_zonas
from motor_inferencia import (encadenamiento_adelante, explicar_razonamiento,
                              obtener_conclusiones, porque, validar_hechos)
from servicio_biometrico import (ENROLAMIENTO, ErrorServicio, ServicioBiometrico,
                                 imagen_a_base64, mapear_enrolamiento, mapear_validacion)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

st.set_page_config(page_title="Validación de identidad facial", layout="wide")

CAMPOS = list(BASE.keys())
CALIDADES = ["buena", "media", "baja"]


# ---------------------------------------------------------------------------
# Estado y callbacks
# ---------------------------------------------------------------------------
def poner_valores(hechos):
    """Copia unos hechos en los campos del formulario."""
    for campo in CAMPOS:
        valor = hechos.get(campo, BASE[campo])
        if campo in ("score_facial", "score_enrolamiento_previo") and valor is None:
            valor = 0
        st.session_state[campo] = valor


def cargar_caso():
    nombre = st.session_state["caso_sel"]
    caso = next(c for c in CASOS_PRUEBA if c["nombre"] == nombre)
    poner_valores(caso["hechos"])
    st.session_state["resultado"] = None
    st.session_state["selfie_resultado"] = None


def limpiar():
    poner_valores(BASE)
    st.session_state["resultado"] = None
    st.session_state["selfie_resultado"] = None


if "rostro_detectado" not in st.session_state:
    poner_valores(BASE)
    st.session_state["resultado"] = None


def leer_formulario():
    hechos = {campo: st.session_state[campo] for campo in CAMPOS}
    hechos["intentos"] = int(hechos["intentos"])
    if not hechos["score_disponible"]:
        hechos["score_facial"] = None
    if not hechos["tiene_enrolamiento_previo"]:
        hechos["score_enrolamiento_previo"] = None
    return hechos


# ---------------------------------------------------------------------------
# Servicio biométrico externo (opcional)
# ---------------------------------------------------------------------------
def cargar_config():
    """Lee la sección [servicio] de los secretos. None si no está configurada."""
    try:
        return dict(st.secrets["servicio"])
    except Exception:
        return None


def obtener_servicio(config):
    # Se guarda en la sesión para reutilizar el token mientras esté vigente
    if "servicio" not in st.session_state:
        st.session_state["servicio"] = ServicioBiometrico(config)
    return st.session_state["servicio"]


def consultar_persona():
    """Paso 1: crea el proceso y averigua si la persona ya tiene rostro registrado."""
    config = cargar_config()
    num_doc = str(st.session_state.get("num_doc", "")).strip()
    st.session_state["api_res"] = None
    st.session_state["proceso"] = None
    if not num_doc.isdigit():
        st.session_state["api_res"] = {"error": ["El número de documento debe tener solo dígitos."]}
        return
    try:
        estado, guid_ciu, guid_proceso = obtener_servicio(config).crear_proceso(
            st.session_state["tipo_doc"], num_doc)
    except ErrorServicio as e:
        st.session_state["api_res"] = {"error": [str(e)]}
        return
    st.session_state["proceso"] = {
        "estado": estado, "guid_ciu": guid_ciu, "guid_proceso": guid_proceso,
        "documento": f"{st.session_state['tipo_doc']} {num_doc}",
    }


def enviar_selfie():
    """Paso 2: guarda la selfie (enrolamiento) o la compara (validación)."""
    proceso = st.session_state.get("proceso")
    imagen = st.session_state.get("img_camara") or st.session_state.get("img_archivo")
    st.session_state["api_res"] = None
    if not proceso:
        st.session_state["api_res"] = {"error": ["Primero consulte a la persona (paso 1)."]}
        return
    if imagen is None:
        st.session_state["api_res"] = {"error": ["Tome o cargue una selfie."]}
        return

    contenido = imagen.getvalue()
    formato = "image/png" if imagen.type == "image/png" else "image/jpeg"
    notas = []
    try:
        from PIL import Image
        import io
        ancho, alto = Image.open(io.BytesIO(contenido)).size
        if ancho * alto < 640 * 480:
            notas.append(f"La imagen mide {ancho} x {alto}; el servicio pide mínimo 640 x 480.")
    except Exception:
        pass

    servicio = obtener_servicio(cargar_config())
    try:
        if proceso["estado"] == ENROLAMIENTO:
            respuesta = servicio.guardar_biometria(proceso["guid_ciu"], imagen_a_base64(contenido), formato)
        else:
            respuesta = servicio.validar_biometria(proceso["guid_ciu"], proceso["guid_proceso"],
                                                   imagen_a_base64(contenido), formato)
    except ErrorServicio as e:
        st.session_state["api_res"] = {"error": [str(e)]}
        return

    # El proceso ya se usó; para otra selfie hay que volver a consultar.
    # La selfie se conserva en la sesión para mostrarla junto al resultado.
    st.session_state["proceso"] = None
    st.session_state["selfie_resultado"] = contenido

    if proceso["estado"] == ENROLAMIENTO:
        ok, notas_enr = mapear_enrolamiento(respuesta)
        st.session_state["api_res"] = {"tipo": "enrolamiento", "ok": ok, "notas": notas + notas_enr,
                                       "documento": proceso["documento"]}
        st.session_state["resultado"] = None
        return

    hechos, notas_val = mapear_validacion(respuesta, BASE)
    if hechos is None:
        st.session_state["api_res"] = {"error": notas_val}
        return
    poner_valores(hechos)
    finales, aplicadas = encadenamiento_adelante(REGLAS, hechos)
    st.session_state["resultado"] = (hechos, finales, aplicadas)
    st.session_state["api_res"] = {"tipo": "validacion", "ok": True, "notas": notas + notas_val,
                                   "documento": proceso["documento"]}


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Casos de prueba")
    st.selectbox("Elija un caso precargado", [c["nombre"] for c in CASOS_PRUEBA], key="caso_sel")
    st.button("Cargar caso", on_click=cargar_caso, use_container_width=True)
    st.button("Limpiar formulario", on_click=limpiar, use_container_width=True)
    st.divider()
    with st.expander("Ver base de conocimiento"):
        for r in REGLAS:
            st.markdown(f"**{r['nombre']}** (nivel {r['nivel']}): {r['descripcion']}")
            st.code(r["logica"], language=None)

# ---------------------------------------------------------------------------
# Entrada
# ---------------------------------------------------------------------------
st.title("Sistema experto de validación de identidad facial")
st.caption("Ingrese el resultado de la captura facial. El sistema decide si la validación "
           "se aprueba, pasa a revisión manual o se rechaza, y explica por qué.")

with st.expander("Validar con una selfie (servicio biométrico externo)"):
    config_servicio = cargar_config()
    if not config_servicio:
        st.info("El servicio no está configurado. Agregue la sección [servicio] en "
                ".streamlit/secrets.toml (vea secrets.example.toml). El formulario manual "
                "funciona igual sin el servicio.")
    elif config_servicio.get("clave_app") and \
            st.text_input("Clave de acceso", type="password", key="clave_app") != config_servicio["clave_app"]:
        st.caption("Ingrese la clave de acceso para usar el servicio.")
    else:
        st.caption("Paso 1: se consulta si la persona ya tiene su rostro registrado en el servicio. "
                   "Paso 2: si no lo tiene, la selfie se guarda (enrolamiento); si ya lo tiene, la "
                   "selfie se compara contra el rostro guardado (validación) y el resultado pasa por "
                   "las 15 reglas. Las imágenes las guarda el servicio, no esta aplicación.")

        st.markdown("##### Paso 1. Consultar a la persona")
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.selectbox("Tipo de documento", ["CC", "CE", "PP", "PEP"], key="tipo_doc")
        with c2:
            st.text_input("Número de documento", key="num_doc")
        with c3:
            st.write("")
            st.write("")
            st.button("Consultar", on_click=consultar_persona, use_container_width=True)

        proceso = st.session_state.get("proceso")
        if proceso and proceso["estado"] == ENROLAMIENTO:
            st.warning(f"{proceso['documento']}: no tiene rostro registrado. Es un ENROLAMIENTO: "
                       "la selfie del paso 2 se guardará como su rostro de referencia.")
        elif proceso:
            st.info(f"{proceso['documento']}: ya tiene rostro registrado. Es una VALIDACIÓN: "
                    "la selfie del paso 2 se comparará contra el rostro guardado.")

        if proceso:
            st.markdown("##### Paso 2. Selfie")
            origen = st.radio("Origen de la selfie", ["Tomar con la cámara", "Cargar archivo"],
                              horizontal=True)
            if origen == "Tomar con la cámara":
                st.camera_input("Tome la selfie", key="img_camara")
            else:
                archivo = st.file_uploader("Imagen JPG o PNG", type=["jpg", "jpeg", "png"], key="img_archivo")
                if archivo is not None:
                    st.image(archivo, caption="Vista previa de la selfie", width=260)
            etiqueta = "Guardar rostro" if proceso["estado"] == ENROLAMIENTO else "Comparar rostro"
            st.button(etiqueta, on_click=enviar_selfie, type="primary")

        res = st.session_state.get("api_res")
        if res and not res.get("error") and st.session_state.get("selfie_resultado"):
            st.image(st.session_state["selfie_resultado"], caption="Selfie enviada", width=220)
        if res and res.get("error"):
            st.error("\n\n".join(res["error"]))
        elif res and res.get("tipo") == "enrolamiento":
            if res["ok"]:
                st.success(f"Enrolamiento de {res['documento']} completo. " + " ".join(res["notas"]) +
                           " Para validarla, vuelva al paso 1 con el mismo documento: ahora aparecerá "
                           "como validación y la nueva selfie se comparará contra este rostro.")
            else:
                st.error("No se pudo guardar el rostro. " + " ".join(res["notas"]))
        elif res and res.get("tipo") == "validacion":
            st.success(f"Validación de {res['documento']}: la selfie se comparó contra el rostro "
                       "registrado. " + " ".join(res["notas"]) +
                       " El formulario se llenó con la respuesta y el resultado está abajo.")

st.subheader("1. Datos de la captura")
st.caption("Los grupos siguen el orden en que el sistema razona: primero revisa si la foto "
           "sirve, después si hay fraude, luego compara el rostro y al final cuenta los intentos.")

# Cada grupo responde una pregunta. Están en una cuadrícula de 2 x 2 con borde.
fila1_a, fila1_b = st.columns(2)
with fila1_a:
    with st.container(border=True):
        st.markdown("#### A. Calidad de la captura")
        st.caption("¿La foto sirve para comparar? Regla R1")
        st.checkbox("Se detectó un rostro", key="rostro_detectado",
                    help="Si no hay rostro, la captura es inválida (R1).")
        st.radio("Calidad de la imagen", CALIDADES, key="calidad_imagen", horizontal=True,
                 help="Luz, enfoque y nitidez. Calidad baja deja la captura inválida (R1).")
        st.checkbox("Usa gafas oscuras, tapabocas o gorra", key="uso_accesorios",
                    help="Tapan partes del rostro; la captura queda inválida (R1).")
with fila1_b:
    with st.container(border=True):
        st.markdown("#### B. Prueba de vida y fraude")
        st.caption("¿Es una persona real y no tiene alertas? Reglas R2 y R3")
        st.checkbox("Superó la prueba de vida", key="prueba_vida_superada",
                    help="Si hay rostro y no la superó, hay posible fraude (R3).")
        st.checkbox("Sospecha de suplantación", key="sospecha_suplantacion",
                    help="Foto impresa, pantalla o máscara: posible fraude (R2).")
        st.checkbox("Está en la lista de riesgo propia", key="en_lista_riesgo",
                    help="La identidad o el rostro tiene un fraude confirmado antes: posible fraude (R2).")
        st.checkbox("El rostro está registrado con otro documento", key="rostro_en_otra_identidad",
                    help="La búsqueda en la base facial (1 a N) lo encontró con otra identidad: posible fraude (R2).")

fila2_a, fila2_b = st.columns(2)
with fila2_a:
    with st.container(border=True):
        st.markdown("#### C. Comparación del rostro")
        st.caption("¿Qué tanto se parece la selfie? Reglas R4 a R13")
        st.checkbox("El motor biométrico devolvió score", key="score_disponible",
                    help="Sin score el sistema no puede decidir.")
        st.number_input("Score facial (0 a 100)", min_value=0, max_value=100, step=1,
                        key="score_facial", disabled=not st.session_state["score_disponible"],
                        help="Similitud contra la foto de referencia: la del documento o la biometría "
                             "registrada en el servicio. 85 o más: aprobación. 60 a 84: zona gris. "
                             "Menos de 60: rechazo.")
        st.checkbox("Hay imagen de un enrolamiento anterior", key="tiene_enrolamiento_previo",
                    help="La persona ya se había enrolado y se tiene su imagen para comparar.")
        st.number_input("Score contra el enrolamiento anterior (0 a 100)", min_value=0, max_value=100,
                        step=1, key="score_enrolamiento_previo",
                        disabled=not st.session_state["tiene_enrolamiento_previo"],
                        help="85 o más confirma la identidad y resuelve la zona gris (R8 y R11). "
                             "Menos de 60 indica posible fraude (R9).")
with fila2_b:
    with st.container(border=True):
        st.markdown("#### D. Historial de intentos")
        st.caption("¿Cuántas veces lo ha intentado hoy? Regla R15")
        st.number_input("Intentos en el día", min_value=1, max_value=5, step=1, key="intentos",
                        help="Con 3 o más intentos fallidos se bloquea por 24 horas (R15).")

if st.button("Validar identidad", type="primary"):
    st.session_state["selfie_resultado"] = None
    hechos = leer_formulario()
    errores = validar_hechos(hechos)
    if errores:
        for e in errores:
            st.error(e)
        st.session_state["resultado"] = None
    else:
        with st.spinner("Aplicando reglas..."):
            finales, aplicadas = encadenamiento_adelante(REGLAS, hechos)
        st.session_state["resultado"] = (hechos, finales, aplicadas)

def mostrar_conclusiones(conclusiones):
    """Muestra la decisión principal y las conclusiones adicionales."""
    if not conclusiones:
        st.warning("Sin conclusión. Con estos datos ninguna regla se pudo aplicar. "
                   "Verifique que el motor biométrico haya devuelto score y que la captura esté completa.")
        return
    mostrar = {"aprobado": st.success, "rechazo": st.error, "aviso": st.warning, "gris": st.info}
    principal = conclusiones[0]
    mostrar[principal["tipo"]](f"### {principal['titulo']}\n{principal['mensaje']}\n\n"
                               f"Certeza: {principal['certeza']:.0%}")
    for c in conclusiones[1:]:
        mostrar[c["tipo"]](f"**{c['titulo']}**: {c['mensaje']} (certeza {c['certeza']:.0%})")


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------
resultado = st.session_state.get("resultado")
if resultado:
    hechos, finales, aplicadas = resultado
    conclusiones = obtener_conclusiones(finales, CONCLUSIONES)

    st.divider()
    st.subheader("2. Resultado")
    selfie = st.session_state.get("selfie_resultado")
    if selfie:
        col_foto, col_res = st.columns([1, 3])
        with col_foto:
            st.image(selfie, caption="Selfie validada", use_container_width=True)
        zona_resultado = col_res.container()
    else:
        zona_resultado = st.container()
    with zona_resultado:
        mostrar_conclusiones(conclusiones)

    if finales.get("captura_valida"):
        fig = grafica_zonas(hechos["score_facial"], anulado_por_fraude=bool(finales.get("posible_fraude")),
                            score_previo=hechos.get("score_enrolamiento_previo"))
        st.pyplot(fig, use_container_width=False)

    st.divider()
    st.subheader("3. Explicación del razonamiento")
    if aplicadas:
        tabla = pd.DataFrame([{
            "Orden": i,
            "Regla": r["nombre"],
            "Nivel": r["nivel"],
            "Condiciones": " y ".join(r["condiciones"]),
            "Concluye": r["conclusion"],
            "Certeza": f"{r['certeza']:.2f}",
        } for i, r in enumerate(aplicadas, start=1)])
        st.dataframe(tabla, hide_index=True, use_container_width=True)
    st.text(explicar_razonamiento(aplicadas))

    derivados = [h for h in HECHOS_DERIVADOS if finales.get(h) is True]
    if derivados:
        st.markdown("**¿Por qué?**")
        col_a, col_b = st.columns([3, 1])
        with col_a:
            elegido = st.selectbox("Elija una conclusión", derivados,
                                   format_func=lambda h: f"{h}: {HECHOS_DERIVADOS[h]}",
                                   label_visibility="collapsed")
        with col_b:
            pedir = st.button("¿Por qué?", use_container_width=True)
        if pedir:
            st.code(porque(elegido, hechos, aplicadas), language=None)
else:
    st.info("Llene los datos o cargue un caso de prueba y presione Validar identidad.")
