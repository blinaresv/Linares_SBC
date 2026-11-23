"""
Casos de prueba precargados. Los usa la interfaz (botón de casos) y las pruebas automáticas.
Cada caso tiene los hechos de entrada, las reglas que se esperan y la decisión esperada.
"""

# Valores iniciales del formulario. El orden sigue los grupos A, B, C y D de la interfaz.
BASE = {
    "rostro_detectado": True,
    "calidad_imagen": "buena",
    "uso_accesorios": False,
    "prueba_vida_superada": True,
    "sospecha_suplantacion": False,
    "en_lista_riesgo": False,
    "rostro_en_otra_identidad": False,
    "score_disponible": True,
    "score_facial": 0,
    "tiene_enrolamiento_previo": False,
    "score_enrolamiento_previo": None,
    "intentos": 1,
}


def _caso(**cambios):
    hechos = dict(BASE)
    hechos.update(cambios)
    return hechos


CASOS_PRUEBA = [
    {
        "id": 1,
        "nombre": "Caso 1: validación aprobada",
        "descripcion": "Score alto, prueba de vida superada y buena calidad",
        "hechos": _caso(score_facial=92),
        "reglas_esperadas": ["R4", "R5", "R10"],
        "decision_esperada": "aprobado",
    },
    {
        "id": 2,
        "nombre": "Caso 2: zona gris, revisión manual",
        "descripcion": "Score de 72 sin enrolamiento anterior",
        "hechos": _caso(score_facial=72),
        "reglas_esperadas": ["R4", "R6", "R12"],
        "decision_esperada": "revision_manual",
    },
    {
        "id": 3,
        "nombre": "Caso 3: zona gris resuelta con enrolamiento",
        "descripcion": "Score de 72, pero coincide con la imagen del enrolamiento anterior (91)",
        "hechos": _caso(score_facial=72, tiene_enrolamiento_previo=True, score_enrolamiento_previo=91),
        "reglas_esperadas": ["R4", "R6", "R8", "R11"],
        "decision_esperada": "aprobado",
    },
    {
        "id": 4,
        "nombre": "Caso 4: el rostro no coincide",
        "descripcion": "Score de 40 con captura válida",
        "hechos": _caso(score_facial=40),
        "reglas_esperadas": ["R4", "R7", "R13"],
        "decision_esperada": "rechazo_no_coincide",
    },
    {
        "id": 5,
        "nombre": "Caso 5: fraude con score alto",
        "descripcion": "Score de 90 pero con sospecha de suplantación, sin prueba de vida y 3 intentos",
        "hechos": _caso(score_facial=90, sospecha_suplantacion=True,
                        prueba_vida_superada=False, intentos=3),
        "reglas_esperadas": ["R2", "R3", "R4", "R5", "R14", "R15"],
        "decision_esperada": "rechazo_fraude",
    },
    {
        "id": 6,
        "nombre": "Caso 6: persona en lista de riesgo",
        "descripcion": "Score de 95, pero la identidad está en la lista de riesgo propia",
        "hechos": _caso(score_facial=95, en_lista_riesgo=True),
        "reglas_esperadas": ["R2", "R4", "R5", "R14"],
        "decision_esperada": "rechazo_fraude",
    },
    {
        "id": 7,
        "nombre": "Caso 7: no coincide con el enrolamiento",
        "descripcion": "Score de 91 contra el documento, pero 45 contra la imagen del enrolamiento anterior",
        "hechos": _caso(score_facial=91, tiene_enrolamiento_previo=True, score_enrolamiento_previo=45),
        "reglas_esperadas": ["R4", "R5", "R9", "R14"],
        "decision_esperada": "rechazo_fraude",
    },
    {
        "id": 8,
        "nombre": "Caso 8: sin conclusión",
        "descripcion": "Hay rostro y calidad media, pero el motor biométrico no devolvió score",
        "hechos": _caso(calidad_imagen="media", score_disponible=False, score_facial=None),
        "reglas_esperadas": [],
        "decision_esperada": None,
    },
    {
        "id": 9,
        "nombre": "Caso 9: borde en 85",
        "descripcion": "Score exactamente en el umbral de aprobación",
        "hechos": _caso(score_facial=85),
        "reglas_esperadas": ["R4", "R5", "R10"],
        "decision_esperada": "aprobado",
    },
    {
        "id": 10,
        "nombre": "Caso 10: borde en 60",
        "descripcion": "Score exactamente en el inicio de la zona gris",
        "hechos": _caso(score_facial=60),
        "reglas_esperadas": ["R4", "R6", "R12"],
        "decision_esperada": "revision_manual",
    },
    {
        "id": 11,
        "nombre": "Caso 11: captura inválida y bloqueo",
        "descripcion": "Calidad baja, con gafas oscuras y 4 intentos",
        "hechos": _caso(score_facial=88, calidad_imagen="baja", uso_accesorios=True, intentos=4),
        "reglas_esperadas": ["R1", "R15"],
        "decision_esperada": "captura_invalida",
    },
    {
        "id": 12,
        "nombre": "Caso 12: no se detectó rostro",
        "descripcion": "La cámara no encontró un rostro en la captura",
        "hechos": _caso(rostro_detectado=False, score_disponible=False, score_facial=None),
        "reglas_esperadas": ["R1"],
        "decision_esperada": "captura_invalida",
    },
    {
        "id": 13,
        "nombre": "Caso 13: máximo de reglas",
        "descripcion": ("Score de 40, enrolamiento anterior de 30, suplantación, rostro con otro documento, "
                        "sin prueba de vida y 3 intentos"),
        "hechos": _caso(score_facial=40, tiene_enrolamiento_previo=True, score_enrolamiento_previo=30,
                        sospecha_suplantacion=True, rostro_en_otra_identidad=True,
                        prueba_vida_superada=False, intentos=3),
        "reglas_esperadas": ["R2", "R3", "R4", "R7", "R9", "R13", "R14", "R15"],
        "decision_esperada": "rechazo_fraude",
    },
]
