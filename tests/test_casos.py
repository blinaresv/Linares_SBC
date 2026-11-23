"""Pruebas automáticas de los casos documentados. Ejecutar con: python -m pytest tests"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from base_conocimiento import REGLAS, CONCLUSIONES, PREDICADOS
from casos import CASOS_PRUEBA
from motor_inferencia import (encadenamiento_adelante, explicar_razonamiento, porque,
                              obtener_conclusiones, validar_hechos, evaluar_condicion)


def test_tamano_base_conocimiento():
    assert 8 <= len(PREDICADOS) <= 12
    assert len(REGLAS) >= 12


@pytest.mark.parametrize("caso", CASOS_PRUEBA, ids=lambda c: c["nombre"])
def test_caso(caso):
    hechos, aplicadas = encadenamiento_adelante(REGLAS, caso["hechos"])
    nombres = [r["nombre"] for r in aplicadas]
    assert nombres == caso["reglas_esperadas"]
    conclusiones = obtener_conclusiones(hechos, CONCLUSIONES)
    decision = conclusiones[0]["hecho"] if conclusiones else None
    assert decision == caso["decision_esperada"]


def _caso(n):
    return next(c for c in CASOS_PRUEBA if c["id"] == n)


def test_fraude_gana_a_score_alto():
    caso = _caso(5)
    hechos, _ = encadenamiento_adelante(REGLAS, caso["hechos"])
    assert hechos.get("score_alto") is True
    assert hechos.get("aprobado") is None


def test_sin_conclusion_tiene_mensaje():
    hechos, aplicadas = encadenamiento_adelante(REGLAS, _caso(8)["hechos"])
    assert aplicadas == []
    assert "No se aplicó ninguna regla" in explicar_razonamiento(aplicadas)


def test_porque_llega_a_datos_ingresados():
    caso = CASOS_PRUEBA[0]
    _, aplicadas = encadenamiento_adelante(REGLAS, caso["hechos"])
    texto = porque("aprobado", caso["hechos"], aplicadas)
    assert "R10" in texto and "R5" in texto and "R4" in texto
    assert "score_facial = 92 (dato ingresado)" in texto


def test_enrolamiento_resuelve_zona_gris():
    hechos, _ = encadenamiento_adelante(REGLAS, _caso(3)["hechos"])
    assert hechos.get("aprobado") is True
    assert hechos.get("revision_manual") is None


def test_un_caso_activa_la_mayoria_de_reglas():
    maximo = max(len(encadenamiento_adelante(REGLAS, c["hechos"])[1]) for c in CASOS_PRUEBA)
    assert maximo > len(REGLAS) / 2


def test_todas_las_reglas_se_usan():
    usadas = set()
    for c in CASOS_PRUEBA:
        usadas |= {r["nombre"] for r in encadenamiento_adelante(REGLAS, c["hechos"])[1]}
    assert usadas == {r["nombre"] for r in REGLAS}


def test_ciclo_no_se_repite():
    # Dos reglas que se alimentan entre sí: el motor debe terminar igual
    reglas = [
        {"nombre": "A", "nivel": 1, "descripcion": "", "condiciones": [("x", "==", True)],
         "conclusion": ("y", True), "certeza": 1.0},
        {"nombre": "B", "nivel": 1, "descripcion": "", "condiciones": [("y", "==", True)],
         "conclusion": ("x", True), "certeza": 1.0},
    ]
    _, aplicadas = encadenamiento_adelante(reglas, {"x": True})
    # termina y cada regla aparece una sola vez
    assert [r["nombre"] for r in aplicadas] == ["A", "B"]


def test_validacion_entrada():
    assert validar_hechos({"score_disponible": True, "score_facial": 120})
    assert validar_hechos({"score_disponible": True, "score_facial": None})
    assert validar_hechos({"intentos": 0})
    assert validar_hechos({"tiene_enrolamiento_previo": True, "score_enrolamiento_previo": None})
    assert not validar_hechos(CASOS_PRUEBA[0]["hechos"])


def test_mundo_cerrado():
    assert evaluar_condicion(("posible_fraude", "==", False), {}) is True
    assert evaluar_condicion(("posible_fraude", "==", True), {}) is False
