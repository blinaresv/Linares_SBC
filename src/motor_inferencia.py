"""
Motor de inferencia con encadenamiento hacia adelante.

Funciones principales:
- encadenamiento_adelante(reglas, hechos_iniciales) -> (hechos_finales, reglas_aplicadas)
- explicar_razonamiento(reglas_aplicadas) -> texto
- porque(conclusion, hechos_iniciales, reglas_aplicadas) -> cadena de razonamiento

Cómo trabaja:
1. Ordena las reglas por nivel (1, 2, 3).
2. En cada nivel recorre las reglas una y otra vez hasta que ninguna nueva se dispare
   (punto fijo). Así las negaciones del nivel 2 y 3 ya ven todo lo que derivó el nivel 1.
3. Cada regla se dispara una sola vez (refracción). Esto, junto con un tope de
   iteraciones, evita ciclos infinitos.
"""

import logging

logger = logging.getLogger("motor_inferencia")

MAX_ITERACIONES = 100  # tope de seguridad por nivel


class CicloInfinitoError(Exception):
    """Se lanza si el motor supera el tope de iteraciones."""


# ---------------------------------------------------------------------------
# Evaluación de condiciones
# ---------------------------------------------------------------------------
def evaluar_condicion(condicion, hechos):
    """Devuelve True si la condición se cumple con los hechos actuales."""
    hecho, operador, *resto = condicion

    # Disyunción: ('cualquiera', [cond1, cond2, ...])
    if hecho == "cualquiera":
        return any(evaluar_condicion(c, hechos) for c in operador)

    valor_esperado = resto[0]
    valor = hechos.get(hecho)

    # Supuesto de mundo cerrado: un booleano que no está se toma como False
    if valor is None:
        if operador == "==" and valor_esperado is False:
            return True
        return False

    if operador == "==":
        return valor == valor_esperado
    if operador == "!=":
        return valor != valor_esperado
    if operador == ">=":
        return valor >= valor_esperado
    if operador == ">":
        return valor > valor_esperado
    if operador == "<":
        return valor < valor_esperado
    if operador == "<=":
        return valor <= valor_esperado
    raise ValueError(f"Operador no soportado: {operador}")


def _hechos_usados(condiciones, hechos):
    """Lista de hechos que sostienen la regla (para la explicación)."""
    usados = []
    for cond in condiciones:
        if cond[0] == "cualquiera":
            # en la disyunción solo se cuentan las opciones que sí se cumplieron
            usados += _hechos_usados([c for c in cond[1] if evaluar_condicion(c, hechos)], hechos)
        else:
            usados.append(cond[0])
    return usados


def _texto_condicion(cond):
    """Convierte una condición en texto legible."""
    if cond[0] == "cualquiera":
        return "(" + " o ".join(_texto_condicion(c) for c in cond[1]) + ")"
    hecho, op, valor = cond
    if valor is True and op == "==":
        return hecho
    if valor is False and op == "==":
        return f"no {hecho}"
    return f"{hecho} {op} {valor}"


# ---------------------------------------------------------------------------
# Encadenamiento hacia adelante
# ---------------------------------------------------------------------------
def encadenamiento_adelante(reglas, hechos_iniciales):
    """
    Aplica encadenamiento hacia adelante.
    Returns: (hechos_finales, reglas_aplicadas)
      hechos_finales: dict con hechos iniciales + derivados
      reglas_aplicadas: lista de dicts en el orden en que se dispararon
    """
    hechos = dict(hechos_iniciales)
    certezas = {h: 1.0 for h in hechos}       # los hechos de entrada tienen certeza 1
    disparadas = set()
    reglas_aplicadas = []

    niveles = sorted({r.get("nivel", 1) for r in reglas})
    for nivel in niveles:
        reglas_nivel = [r for r in reglas if r.get("nivel", 1) == nivel]
        iteracion = 0
        hubo_cambio = True
        while hubo_cambio:
            iteracion += 1
            if iteracion > MAX_ITERACIONES:
                raise CicloInfinitoError(f"Se superaron {MAX_ITERACIONES} iteraciones en el nivel {nivel}")
            hubo_cambio = False
            for regla in reglas_nivel:
                if regla["nombre"] in disparadas:
                    continue
                if not all(evaluar_condicion(c, hechos) for c in regla["condiciones"]):
                    continue

                hecho, valor = regla["conclusion"]
                usados = _hechos_usados(regla["condiciones"], hechos)
                disparadas.add(regla["nombre"])

                # Si el hecho ya existe con otro valor, no se sobrescribe (evita oscilaciones)
                if hecho in hechos and hechos[hecho] != valor:
                    logger.warning("%s quiso cambiar %s a %s; se ignora", regla["nombre"], hecho, valor)
                    continue

                # Factor de certeza: certeza de la regla x la menor certeza de sus premisas
                cf_premisas = min((certezas.get(h, 1.0) for h in usados), default=1.0)
                cf = round(regla["certeza"] * cf_premisas, 3)
                ya_estaba = hecho in hechos
                hechos[hecho] = valor
                certezas[hecho] = max(certezas.get(hecho, 0), cf) if ya_estaba else cf

                reglas_aplicadas.append({
                    "nombre": regla["nombre"],
                    "nivel": nivel,
                    "descripcion": regla["descripcion"],
                    "condiciones": [_texto_condicion(c) for c in regla["condiciones"]],
                    "hechos_usados": usados,
                    "conclusion": hecho,
                    "certeza": cf,
                })
                logger.info("Nivel %s, iteración %s: %s -> %s (certeza %.2f)",
                            nivel, iteracion, regla["nombre"], hecho, cf)
                hubo_cambio = True

    if not reglas_aplicadas:
        logger.info("Ninguna regla se pudo aplicar con los hechos dados")

    hechos["_certezas"] = certezas
    return hechos, reglas_aplicadas


# ---------------------------------------------------------------------------
# Explicación
# ---------------------------------------------------------------------------
def explicar_razonamiento(reglas_aplicadas):
    """
    Genera explicación legible del razonamiento.
    Returns: texto explicativo
    """
    if not reglas_aplicadas:
        return ("No se aplicó ninguna regla. Con los datos ingresados el sistema no puede "
                "llegar a una conclusión; revise que haya score y que la captura esté completa.")

    lineas = []
    for i, r in enumerate(reglas_aplicadas, start=1):
        condiciones = " y ".join(r["condiciones"])
        lineas.append(f"{i}. [{r['nombre']}, nivel {r['nivel']}] Como se cumple {condiciones}, "
                      f"se concluye {r['conclusion']} (certeza {r['certeza']:.2f}).")
    return "\n".join(lineas)


def porque(conclusion, hechos_iniciales, reglas_aplicadas, _visitados=None, _sangria=0):
    """
    Explica por qué se llegó a una conclusión específica, bajando por las reglas
    hasta llegar a los hechos que ingresó el usuario.
    Returns: cadena de razonamiento (texto con sangría)
    """
    visitados = _visitados if _visitados is not None else set()
    espacio = "    " * _sangria

    if conclusion in hechos_iniciales:
        return f"{espacio}- {conclusion} = {hechos_iniciales[conclusion]} (dato ingresado)"

    reglas = [r for r in reglas_aplicadas if r["conclusion"] == conclusion]
    if not reglas:
        if _sangria == 0:
            return f"No se concluyó '{conclusion}' con los datos ingresados."
        # hecho negado por mundo cerrado (ej. no posible_fraude)
        return f"{espacio}- {conclusion} no se derivó, se toma como falso (mundo cerrado)"

    if conclusion in visitados:
        return f"{espacio}- {conclusion} (ya explicado)"
    visitados.add(conclusion)

    lineas = []
    for r in reglas:
        lineas.append(f"{espacio}- {conclusion} porque se aplicó {r['nombre']}: {r['descripcion']}")
        for h in r["hechos_usados"]:
            lineas.append(porque(h, hechos_iniciales, reglas_aplicadas, visitados, _sangria + 1))
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Validación de entrada
# ---------------------------------------------------------------------------
def validar_hechos(hechos):
    """Revisa los datos de entrada. Devuelve una lista de errores (vacía si todo está bien)."""
    errores = []
    if hechos.get("score_disponible"):
        s = hechos.get("score_facial")
        if s is None:
            errores.append("Marcó que hay score pero no ingresó el valor.")
        elif not 0 <= s <= 100:
            errores.append("El score facial debe estar entre 0 y 100.")
    if hechos.get("tiene_enrolamiento_previo"):
        e = hechos.get("score_enrolamiento_previo")
        if e is None:
            errores.append("Marcó que hay enrolamiento anterior pero no ingresó su score.")
        elif not 0 <= e <= 100:
            errores.append("El score del enrolamiento anterior debe estar entre 0 y 100.")
    n = hechos.get("intentos")
    if n is not None and not 1 <= n <= 5:
        errores.append("Los intentos deben estar entre 1 y 5.")
    if hechos.get("calidad_imagen") not in (None, "buena", "media", "baja"):
        errores.append("La calidad de imagen debe ser buena, media o baja.")
    return errores


# ---------------------------------------------------------------------------
# Conclusiones para mostrar
# ---------------------------------------------------------------------------
def obtener_conclusiones(hechos_finales, catalogo):
    """
    Devuelve las conclusiones del catálogo que quedaron en True, ordenadas por prioridad.
    La primera es la decisión principal. Lista vacía si no hubo conclusión.
    """
    certezas = hechos_finales.get("_certezas", {})
    encontradas = []
    for hecho, info in catalogo.items():
        if hechos_finales.get(hecho) is True:
            encontradas.append({"hecho": hecho, "certeza": certezas.get(hecho, 1.0), **info})
    return sorted(encontradas, key=lambda c: c["prioridad"])
