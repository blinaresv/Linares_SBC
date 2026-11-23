# Casos de prueba

Todos los casos están precargados en la interfaz, en la barra lateral con el botón Cargar caso, y se ejecutan de forma automática con:

```
python -m pytest tests
```

La tabla se generó ejecutando el motor sobre cada caso. La columna Resultado obtenido muestra la decisión principal seguida de las conclusiones adicionales.

| Caso | Descripción | Hechos iniciales | Reglas esperadas | Conclusión esperada | Resultado obtenido | Estado |
|---|---|---|---|---|---|---|
| 1 | Score alto, prueba de vida superada y buena calidad | score 92, calidad buena, prueba de vida superada, 1 intento(s) | R4, R5, R10 | Aprobado | Aprobado | ✓ |
| 2 | Score de 72 sin enrolamiento anterior | score 72, calidad buena, prueba de vida superada, 1 intento(s) | R4, R6, R12 | Zona gris: revisión manual | Zona gris: revisión manual | ✓ |
| 3 | Score de 72, pero coincide con la imagen del enrolamiento anterior (91) | score 72, calidad buena, prueba de vida superada, enrolamiento anterior 91, 1 intento(s) | R4, R6, R8, R11 | Aprobado | Aprobado | ✓ |
| 4 | Score de 40 con captura válida | score 40, calidad buena, prueba de vida superada, 1 intento(s) | R4, R7, R13 | Rechazado: el rostro no coincide | Rechazado: el rostro no coincide | ✓ |
| 5 | Score de 90 pero con sospecha de suplantación, sin prueba de vida y 3 intentos | score 90, calidad buena, sin prueba de vida, sospecha de suplantación, 3 intento(s) | R2, R3, R4, R5, R14, R15 | Rechazado por posible fraude | Rechazado por posible fraude + Bloqueo temporal | ✓ |
| 6 | Score de 95, pero la identidad está en la lista de riesgo propia | score 95, calidad buena, prueba de vida superada, en lista de riesgo, 1 intento(s) | R2, R4, R5, R14 | Rechazado por posible fraude | Rechazado por posible fraude | ✓ |
| 7 | Score de 91 contra el documento, pero 45 contra la imagen del enrolamiento anterior | score 91, calidad buena, prueba de vida superada, enrolamiento anterior 45, 1 intento(s) | R4, R5, R9, R14 | Rechazado por posible fraude | Rechazado por posible fraude | ✓ |
| 8 | Hay rostro y calidad media, pero el motor biométrico no devolvió score | sin score, calidad media, prueba de vida superada, 1 intento(s) | ninguna | Sin conclusión | Sin conclusión | ✓ |
| 9 | Score exactamente en el umbral de aprobación | score 85, calidad buena, prueba de vida superada, 1 intento(s) | R4, R5, R10 | Aprobado | Aprobado | ✓ |
| 10 | Score exactamente en el inicio de la zona gris | score 60, calidad buena, prueba de vida superada, 1 intento(s) | R4, R6, R12 | Zona gris: revisión manual | Zona gris: revisión manual | ✓ |
| 11 | Calidad baja, con gafas oscuras y 4 intentos | score 88, calidad baja, con accesorios, prueba de vida superada, 4 intento(s) | R1, R15 | Captura inválida | Captura inválida + Bloqueo temporal | ✓ |
| 12 | La cámara no encontró un rostro en la captura | sin score, sin rostro, calidad buena, prueba de vida superada, 1 intento(s) | R1 | Captura inválida | Captura inválida | ✓ |
| 13 | Score de 40, enrolamiento anterior de 30, suplantación, rostro con otro documento, sin prueba de vida y 3 intentos | score 40, calidad buena, sin prueba de vida, sospecha de suplantación, rostro con otro documento, enrolamiento anterior 30, 3 intento(s) | R2, R3, R4, R7, R9, R13, R14, R15 | Rechazado por posible fraude | Rechazado por posible fraude + Rechazado: el rostro no coincide + Bloqueo temporal | ✓ |

## Qué prueba cada caso

- Caso 1: el camino normal, de la captura válida a la aprobación.
- Caso 2: zona gris sin otra evidencia, que termina en revisión manual (R12).
- Caso 3: la misma zona gris, pero la selfie coincide con el enrolamiento anterior y se aprueba (R8 y R11).
- Caso 4: rechazo porque el rostro no coincide.
- Caso 5: el fraude gana sobre un score de 90, porque R10 exige que no haya posible fraude.
- Caso 6: la lista de riesgo propia anula un score de 95 (R2).
- Caso 7: coincide con el documento pero no con quien se enroló antes con esa identidad (R9).
- Caso 8: sin conclusión. Ninguna regla se dispara y el sistema lo informa en lugar de inventar una decisión.
- Casos 9 y 10: bordes exactos de los umbrales; 85 entra en aprobación y 60 en zona gris.
- Caso 11: captura inválida por calidad baja y accesorios, con bloqueo por 4 intentos (R1 y R15).
- Caso 12: sin rostro detectado (R1).
- Caso 13: activa 8 de las 15 reglas, la mayoría, y pasa por los tres niveles.

Entre los 13 casos se usan las 15 reglas.

## Pruebas adicionales en tests/test_casos.py

- Tamaño de la base de conocimiento: entre 8 y 12 predicados y al menos 12 reglas.
- El fraude anula la aprobación aunque exista score_alto.
- El enrolamiento anterior resuelve la zona gris sin revisión manual.
- Al menos un caso activa más de la mitad de las reglas.
- Todas las reglas se usan en algún caso.
- La función porque() llega hasta los datos ingresados por el usuario.
- Dos reglas que se alimentan entre sí no generan un ciclo infinito.
- Validación de entradas fuera de rango.
- Supuesto de mundo cerrado para hechos que no existen.
