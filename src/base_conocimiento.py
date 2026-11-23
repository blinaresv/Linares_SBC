"""
Base de conocimiento del sistema experto de validación de identidad facial.

Contiene:
- PREDICADOS: hechos de entrada que describe el usuario (12 predicados).
- HECHOS_DERIVADOS: hechos intermedios y conclusiones que produce el motor.
- REGLAS: 15 reglas de producción organizadas en 3 niveles.
- CONCLUSIONES: texto que se le muestra al usuario por cada conclusión.

Formato de una condición: (hecho, operador, valor)
    operadores: '==', '!=', '>=', '>', '<', '<='
    ('cualquiera', [cond1, cond2, ...]) se cumple si al menos una se cumple (disyunción).

Supuesto de mundo cerrado: si un hecho booleano no existe, se toma como False.

Los umbrales son de ejemplo para fines académicos.
"""

# Umbrales de decisión (scores de 0 a 100)
UMBRAL_APROBACION = 85   # score >= 85 -> aprobado
UMBRAL_ZONA_GRIS = 60    # 60 <= score < 85 -> zona gris; score < 60 -> rechazo
MAX_INTENTOS = 3         # desde este número de intentos fallidos se bloquea

# ---------------------------------------------------------------------------
# Predicados de entrada: nombre -> descripción, tipo, dominio y rango
# ---------------------------------------------------------------------------
PREDICADOS = {
    "rostro_detectado": {
        "descripcion": "Se detectó un rostro en la captura",
        "notacion": "rostro_detectado(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "calidad_imagen": {
        "descripcion": "Calidad de la captura (luz, enfoque, nitidez)",
        "notacion": "calidad_imagen(p, q)",
        "tipo": "categórico",
        "dominio": "p ∈ Personas",
        "rango": "q ∈ {buena, media, baja}",
    },
    "uso_accesorios": {
        "descripcion": "La persona usa gafas oscuras, tapabocas o gorra",
        "notacion": "uso_accesorios(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "prueba_vida_superada": {
        "descripcion": "La persona superó la prueba de vida (es una persona real frente a la cámara)",
        "notacion": "prueba_vida_superada(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "sospecha_suplantacion": {
        "descripcion": "Se detectó foto impresa, pantalla o máscara",
        "notacion": "sospecha_suplantacion(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "en_lista_riesgo": {
        "descripcion": "La identidad o el rostro está en la lista de riesgo propia (fraudes confirmados)",
        "notacion": "en_lista_riesgo(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "rostro_en_otra_identidad": {
        "descripcion": "La búsqueda en la base facial (1 a N) encontró el rostro con otro documento",
        "notacion": "rostro_en_otra_identidad(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "score_disponible": {
        "descripcion": "El motor biométrico devolvió un score",
        "notacion": "score_disponible(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "score_facial": {
        "descripcion": "Similitud entre la selfie y la foto de referencia",
        "notacion": "score_facial(p, s)",
        "tipo": "numérico",
        "dominio": "p ∈ Personas",
        "rango": "s ∈ [0, 100]",
    },
    "tiene_enrolamiento_previo": {
        "descripcion": "Ya existe una imagen de la persona de un enrolamiento anterior",
        "notacion": "tiene_enrolamiento_previo(p)",
        "tipo": "booleano",
        "dominio": "p ∈ Personas",
        "rango": "{V, F}",
    },
    "score_enrolamiento_previo": {
        "descripcion": "Similitud entre la selfie y la imagen del enrolamiento anterior",
        "notacion": "score_enrolamiento_previo(p, e)",
        "tipo": "numérico",
        "dominio": "p ∈ Personas",
        "rango": "e ∈ [0, 100]",
    },
    "intentos": {
        "descripcion": "Número de intentos de validación en el día",
        "notacion": "intentos(p, n)",
        "tipo": "entero",
        "dominio": "p ∈ Personas",
        "rango": "n ∈ {1, 2, 3, 4, 5}",
    },
}

# Hechos que el motor puede derivar (intermedios y finales)
HECHOS_DERIVADOS = {
    "captura_invalida": "La captura no sirve para comparar el rostro",
    "posible_fraude": "Hay indicios de fraude o suplantación",
    "captura_valida": "La captura es apta y hay score para comparar",
    "score_alto": f"Score mayor o igual a {UMBRAL_APROBACION}",
    "score_zona_gris": f"Score entre {UMBRAL_ZONA_GRIS} y {UMBRAL_APROBACION - 1}",
    "score_bajo": f"Score menor a {UMBRAL_ZONA_GRIS}",
    "coincide_enrolamiento": "La selfie coincide con la imagen del enrolamiento anterior",
    "aprobado": "Validación aprobada",
    "revision_manual": "Validación en zona gris, va a revisión manual",
    "rechazo_no_coincide": "Rechazo porque el rostro no coincide",
    "rechazo_fraude": "Rechazo por posible fraude",
    "bloqueo_temporal": "Bloqueo temporal por intentos fallidos",
}

# ---------------------------------------------------------------------------
# Reglas de producción
# Cada regla tiene: nombre, nivel, descripción, condiciones, conclusión,
# certeza (factor de certeza entre 0 y 1) y su forma en lógica de predicados.
# El motor resuelve primero el nivel 1, luego el 2 y luego el 3.
# ---------------------------------------------------------------------------
REGLAS = [
    # ---------------- Nivel 1: revisión de la captura y fraude ----------------
    {
        "nombre": "R1",
        "nivel": 1,
        "descripcion": "Sin rostro, con calidad baja o con accesorios la captura no sirve",
        "condiciones": [
            ("cualquiera", [
                ("rostro_detectado", "==", False),
                ("calidad_imagen", "==", "baja"),
                ("uso_accesorios", "==", True),
            ]),
        ],
        "conclusion": ("captura_invalida", True),
        "certeza": 0.95,
        "logica": ("∀p ¬rostro_detectado(p) ∨ calidad_imagen(p, baja) ∨ uso_accesorios(p) "
                   "→ captura_invalida(p)"),
    },
    {
        "nombre": "R2",
        "nivel": 1,
        "descripcion": "Suplantación, lista de riesgo u otra identidad: posible fraude",
        "condiciones": [
            ("cualquiera", [
                ("sospecha_suplantacion", "==", True),
                ("en_lista_riesgo", "==", True),
                ("rostro_en_otra_identidad", "==", True),
            ]),
        ],
        "conclusion": ("posible_fraude", True),
        "certeza": 0.95,
        "logica": ("∀p sospecha_suplantacion(p) ∨ en_lista_riesgo(p) ∨ rostro_en_otra_identidad(p) "
                   "→ posible_fraude(p)"),
    },
    {
        "nombre": "R3",
        "nivel": 1,
        "descripcion": "Hay rostro pero no superó la prueba de vida: posible fraude",
        "condiciones": [
            ("rostro_detectado", "==", True),
            ("prueba_vida_superada", "==", False),
        ],
        "conclusion": ("posible_fraude", True),
        "certeza": 0.9,
        "logica": "∀p rostro_detectado(p) ∧ ¬prueba_vida_superada(p) → posible_fraude(p)",
    },
    # ---------------- Nivel 2: validez de la captura y comparación ----------------
    {
        "nombre": "R4",
        "nivel": 2,
        "descripcion": "Hay rostro, la captura no es inválida y hay score: captura válida",
        "condiciones": [
            ("rostro_detectado", "==", True),
            ("captura_invalida", "==", False),
            ("score_disponible", "==", True),
        ],
        "conclusion": ("captura_valida", True),
        "certeza": 1.0,
        "logica": "∀p rostro_detectado(p) ∧ ¬captura_invalida(p) ∧ score_disponible(p) → captura_valida(p)",
    },
    {
        "nombre": "R5",
        "nivel": 2,
        "descripcion": f"Captura válida y score >= {UMBRAL_APROBACION}: score alto",
        "condiciones": [
            ("captura_valida", "==", True),
            ("score_facial", ">=", UMBRAL_APROBACION),
        ],
        "conclusion": ("score_alto", True),
        "certeza": 0.98,
        "logica": f"∀p ∀s captura_valida(p) ∧ score_facial(p, s) ∧ s ≥ {UMBRAL_APROBACION} → score_alto(p)",
    },
    {
        "nombre": "R6",
        "nivel": 2,
        "descripcion": f"Captura válida y score entre {UMBRAL_ZONA_GRIS} y {UMBRAL_APROBACION - 1}: zona gris",
        "condiciones": [
            ("captura_valida", "==", True),
            ("score_facial", ">=", UMBRAL_ZONA_GRIS),
            ("score_facial", "<", UMBRAL_APROBACION),
        ],
        "conclusion": ("score_zona_gris", True),
        "certeza": 0.9,
        "logica": (f"∀p ∀s captura_valida(p) ∧ score_facial(p, s) ∧ {UMBRAL_ZONA_GRIS} ≤ s < "
                   f"{UMBRAL_APROBACION} → score_zona_gris(p)"),
    },
    {
        "nombre": "R7",
        "nivel": 2,
        "descripcion": f"Captura válida y score < {UMBRAL_ZONA_GRIS}: score bajo",
        "condiciones": [
            ("captura_valida", "==", True),
            ("score_facial", "<", UMBRAL_ZONA_GRIS),
        ],
        "conclusion": ("score_bajo", True),
        "certeza": 0.95,
        "logica": f"∀p ∀s captura_valida(p) ∧ score_facial(p, s) ∧ s < {UMBRAL_ZONA_GRIS} → score_bajo(p)",
    },
    {
        "nombre": "R8",
        "nivel": 2,
        "descripcion": f"Coincide con la imagen del enrolamiento anterior (>= {UMBRAL_APROBACION})",
        "condiciones": [
            ("captura_valida", "==", True),
            ("tiene_enrolamiento_previo", "==", True),
            ("score_enrolamiento_previo", ">=", UMBRAL_APROBACION),
        ],
        "conclusion": ("coincide_enrolamiento", True),
        "certeza": 0.95,
        "logica": (f"∀p ∀e captura_valida(p) ∧ tiene_enrolamiento_previo(p) ∧ "
                   f"score_enrolamiento_previo(p, e) ∧ e ≥ {UMBRAL_APROBACION} → coincide_enrolamiento(p)"),
    },
    {
        "nombre": "R9",
        "nivel": 2,
        "descripcion": f"No coincide con la imagen del enrolamiento anterior (< {UMBRAL_ZONA_GRIS}): posible fraude",
        "condiciones": [
            ("captura_valida", "==", True),
            ("tiene_enrolamiento_previo", "==", True),
            ("score_enrolamiento_previo", "<", UMBRAL_ZONA_GRIS),
        ],
        "conclusion": ("posible_fraude", True),
        "certeza": 0.9,
        "logica": (f"∀p ∀e captura_valida(p) ∧ tiene_enrolamiento_previo(p) ∧ "
                   f"score_enrolamiento_previo(p, e) ∧ e < {UMBRAL_ZONA_GRIS} → posible_fraude(p)"),
    },
    # ---------------- Nivel 3: decisión ----------------
    {
        "nombre": "R10",
        "nivel": 3,
        "descripcion": "Score alto sin indicios de fraude: aprobado",
        "condiciones": [
            ("score_alto", "==", True),
            ("posible_fraude", "==", False),
        ],
        "conclusion": ("aprobado", True),
        "certeza": 0.97,
        "logica": "∀p score_alto(p) ∧ ¬posible_fraude(p) → aprobado(p)",
    },
    {
        "nombre": "R11",
        "nivel": 3,
        "descripcion": "Zona gris que coincide con el enrolamiento anterior, sin fraude: aprobado",
        "condiciones": [
            ("score_zona_gris", "==", True),
            ("coincide_enrolamiento", "==", True),
            ("posible_fraude", "==", False),
        ],
        "conclusion": ("aprobado", True),
        "certeza": 0.9,
        "logica": "∀p score_zona_gris(p) ∧ coincide_enrolamiento(p) ∧ ¬posible_fraude(p) → aprobado(p)",
    },
    {
        "nombre": "R12",
        "nivel": 3,
        "descripcion": "Zona gris sin enrolamiento que confirme y sin fraude: revisión manual",
        "condiciones": [
            ("score_zona_gris", "==", True),
            ("coincide_enrolamiento", "==", False),
            ("posible_fraude", "==", False),
        ],
        "conclusion": ("revision_manual", True),
        "certeza": 0.9,
        "logica": "∀p score_zona_gris(p) ∧ ¬coincide_enrolamiento(p) ∧ ¬posible_fraude(p) → revision_manual(p)",
    },
    {
        "nombre": "R13",
        "nivel": 3,
        "descripcion": "Score bajo: rechazo porque el rostro no coincide",
        "condiciones": [("score_bajo", "==", True)],
        "conclusion": ("rechazo_no_coincide", True),
        "certeza": 0.95,
        "logica": "∀p score_bajo(p) → rechazo_no_coincide(p)",
    },
    {
        "nombre": "R14",
        "nivel": 3,
        "descripcion": "Posible fraude: rechazo, aunque el score sea alto",
        "condiciones": [("posible_fraude", "==", True)],
        "conclusion": ("rechazo_fraude", True),
        "certeza": 0.95,
        "logica": "∀p posible_fraude(p) → rechazo_fraude(p)",
    },
    {
        "nombre": "R15",
        "nivel": 3,
        "descripcion": f"{MAX_INTENTOS} o más intentos con captura inválida o rechazo: bloqueo temporal",
        "condiciones": [
            ("intentos", ">=", MAX_INTENTOS),
            ("cualquiera", [
                ("captura_invalida", "==", True),
                ("rechazo_no_coincide", "==", True),
                ("rechazo_fraude", "==", True),
            ]),
        ],
        "conclusion": ("bloqueo_temporal", True),
        "certeza": 1.0,
        "logica": (f"∀p ∀n intentos(p, n) ∧ n ≥ {MAX_INTENTOS} ∧ (captura_invalida(p) ∨ "
                   "rechazo_no_coincide(p) ∨ rechazo_fraude(p)) → bloqueo_temporal(p)"),
    },
]

# ---------------------------------------------------------------------------
# Textos para el usuario. 'tipo' define el color en la interfaz.
# 'prioridad' ordena cuál es la decisión principal (menor = más importante).
# ---------------------------------------------------------------------------
CONCLUSIONES = {
    "rechazo_fraude": {
        "titulo": "Rechazado por posible fraude",
        "mensaje": "Hay indicios de fraude: suplantación, lista de riesgo, rostro registrado con otro "
                   "documento o diferencia con el enrolamiento anterior. No se aprueba aunque el score "
                   "sea alto. Reportar el caso al área de seguridad.",
        "tipo": "rechazo",
        "prioridad": 1,
    },
    "rechazo_no_coincide": {
        "titulo": "Rechazado: el rostro no coincide",
        "mensaje": "El score está por debajo del umbral de zona gris. La persona de la selfie "
                   "no corresponde con la foto de referencia.",
        "tipo": "rechazo",
        "prioridad": 2,
    },
    "captura_invalida": {
        "titulo": "Captura inválida",
        "mensaje": "La captura no sirve para comparar. Pedir una nueva con buena luz, "
                   "rostro de frente y sin gafas oscuras, tapabocas ni gorra.",
        "tipo": "aviso",
        "prioridad": 3,
    },
    "revision_manual": {
        "titulo": "Zona gris: revisión manual",
        "mensaje": "El score no alcanza para aprobar ni es tan bajo como para rechazar, y no hay "
                   "un enrolamiento anterior que lo confirme. Un revisor debe comparar las imágenes.",
        "tipo": "gris",
        "prioridad": 4,
    },
    "aprobado": {
        "titulo": "Aprobado",
        "mensaje": "La identidad se confirmó y no hay indicios de fraude. Puede continuar con el proceso.",
        "tipo": "aprobado",
        "prioridad": 5,
    },
    "bloqueo_temporal": {
        "titulo": "Bloqueo temporal",
        "mensaje": f"Lleva {MAX_INTENTOS} o más intentos fallidos. Bloquear nuevos intentos "
                   "por 24 horas.",
        "tipo": "rechazo",
        "prioridad": 6,
    },
}
