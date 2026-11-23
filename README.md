# Sistema experto de validación de identidad facial

Proyecto final de Inteligencia Artificial II.
Brandon Felipe Linares Viasus.

Sistema basado en conocimiento que decide si una validación facial se aprueba, pasa a revisión manual (zona gris) o se rechaza. Recibe el score de similitud y las señales de la captura: rostro, calidad, accesorios, prueba de vida, suplantación, lista de riesgo, base facial, enrolamiento anterior e intentos, y explica cada decisión con las reglas que aplicó.

- 12 predicados y 15 reglas en tres niveles, con factores de certeza. Además del score contra el documento, usa la lista de riesgo propia, la búsqueda en la base facial y la imagen de un enrolamiento anterior.
- Motor de encadenamiento hacia adelante con explicación, función `porque()`, detección de ciclos y logging.
- Interfaz web en Streamlit con 13 casos de prueba precargados y gráfica de zonas de decisión.

Los umbrales (85 para aprobar, 60 para zona gris) son de ejemplo.

## Instalación

Requiere Python 3.10 o superior. En Mac y Linux use `python3` en lugar de `python`.

```bash
python -m venv venv
# Windows: venv\Scripts\activate    Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run src/app.py
```

Se abre en http://localhost:8501. En la barra lateral se puede cargar cualquiera de los casos de prueba.

Pruebas automáticas:

```bash
python -m pytest tests
```

## Validar con una selfie (opcional)

La app puede enviar una selfie a un servicio biométrico externo. La primera vez guarda la selfie de la persona y las siguientes compara contra ella; la respuesta llena el formulario y pasa por las 15 reglas. Para activarlo, copie `.streamlit/secrets.example.toml` como `.streamlit/secrets.toml` y llene los datos. Ese archivo no se sube al repositorio. En Streamlit Cloud los mismos valores van en Settings > Secrets. Sin esta configuración, el resto de la app funciona igual.

## Estructura

```
linares_viasus_proyecto_final_sbc/
├── README.md
├── requirements.txt
├── src/
│   ├── base_conocimiento.py   # predicados, umbrales y reglas
│   ├── motor_inferencia.py    # encadenamiento adelante y explicación
│   ├── app.py                 # interfaz web (Streamlit)
│   ├── grafica.py             # gráfica de zonas de decisión
│   ├── casos.py               # casos de prueba precargados
│   └── servicio_biometrico.py # integración opcional con el servicio biométrico
├── docs/
│   ├── documentacion_tecnica.pdf
│   └── manual_usuario.pdf
└── tests/
    ├── casos_prueba.md
    ├── test_casos.py
    └── test_servicio.py
```

## Cómo agregar una regla

Copie un diccionario en la lista `REGLAS` de `src/base_conocimiento.py` con nombre, nivel, condiciones, conclusión y certeza. Si la conclusión debe mostrarse al usuario, agregue también su texto en `CONCLUSIONES`. No hay que modificar el motor.

## Video de demo

No aplica para esta entrega. La demostración se hace en vivo el día de la sustentación.
