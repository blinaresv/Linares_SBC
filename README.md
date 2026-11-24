# Sistema experto de validación de identidad facial

Proyecto final de Inteligencia Artificial II.
Brandon Felipe Linares Viasus.

Sistema basado en conocimiento que decide si una validación facial se aprueba, pasa a revisión manual (zona gris) o se rechaza. Recibe el score de similitud y las señales de la captura: rostro, calidad, accesorios, prueba de vida, suplantación, lista de riesgo, base facial, enrolamiento anterior e intentos. Cada decisión viene con la explicación de las reglas que se aplicaron.

- 12 predicados y 15 reglas en tres niveles, con factores de certeza.
- Motor de encadenamiento hacia adelante con explicación, función `porque()`, detección de ciclos y logging.
- Interfaz web en Streamlit con 13 casos de prueba precargados y gráfica de zonas de decisión.
- Validación opcional con una selfie a través de un servicio biométrico externo.

Los umbrales (85 para aprobar, 60 para zona gris) son de ejemplo.

## Versión en línea

La aplicación está publicada en Streamlit Community Cloud:

https://linaressbc-b4psbrerwigawdyyl2viqu.streamlit.app

No requiere instalar nada; funciona desde cualquier navegador. Se actualiza sola cada vez que se sube un cambio a la rama `main` de este repositorio.

## Versiones

| Componente | Versión |
|---|---|
| Python | 3.10 o superior. Probado con 3.14, en local y en la nube |
| Streamlit | 1.30 o superior. En la nube corre la 1.67 |
| Matplotlib, pandas, requests, Pillow, pytest | Las indicadas en `requirements.txt` |

## Ejecución local paso a paso

1. Instalar Python 3.10 o superior desde https://www.python.org/downloads y comprobar la versión:

   ```bash
   python3 --version        # Mac o Linux
   python --version         # Windows
   ```

2. Descargar el proyecto. Se puede clonar el repositorio o descomprimir el ZIP de la entrega:

   ```bash
   git clone https://github.com/blinaresv/Linares_SBC.git
   cd Linares_SBC
   ```

3. Crear y activar un entorno virtual:

   ```bash
   python3 -m venv venv
   source venv/bin/activate          # Mac o Linux
   venv\Scripts\activate             # Windows
   ```

4. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

5. Ejecutar la aplicación:

   ```bash
   streamlit run src/app.py
   ```

   Se abre en http://localhost:8501. Para cerrarla se presiona Ctrl + C en la terminal.

6. Correr las pruebas automáticas, si se quiere comprobar el motor:

   ```bash
   python3 -m pytest tests
   ```

   Deben pasar las 33 pruebas.

Las siguientes veces solo hacen falta tres pasos: entrar a la carpeta, activar el entorno virtual y ejecutar `streamlit run src/app.py`.

## Validar con una selfie (opcional)

En la sección "Validar con una selfie" se consulta primero a la persona por su documento. Si no tiene rostro registrado, se guardan en el servicio la selfie y las dos caras del documento (enrolamiento); si ya lo tiene, solo se pide la selfie, que se compara contra el rostro guardado (validación), y la respuesta pasa por las 15 reglas. Las imágenes las conserva el servicio, no la aplicación.

Las direcciones y credenciales del servicio no están en el repositorio:

- En local, se copia `.streamlit/secrets.example.toml` como `.streamlit/secrets.toml` y se llenan los datos. Ese archivo está en `.gitignore`.
- En Streamlit Cloud, el mismo contenido va en Manage app > Settings > Secrets.
- `clave_app` vacía deja la sección abierta; con un valor, la app lo pide antes de usar el servicio.

Sin esta configuración, el formulario manual y los casos de prueba funcionan igual.

## Publicar en Streamlit Community Cloud

1. Subir el proyecto a GitHub.
2. En https://share.streamlit.io, elegir Create app y luego Deploy a public app from GitHub.
3. Llenar Repository `blinaresv/Linares_SBC`, Branch `main` y Main file path `src/app.py`.
4. En Advanced settings, elegir la versión de Python y pegar los secretos.
5. Presionar Deploy.

## Estructura

```
Linares_SBC/
├── README.md
├── requirements.txt
├── .streamlit/
│   └── secrets.example.toml   # plantilla de configuración del servicio
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

Se copia un diccionario en la lista `REGLAS` de `src/base_conocimiento.py`, con nombre, nivel, condiciones, conclusión y certeza. Si la conclusión debe verse en pantalla, se agrega también su texto en `CONCLUSIONES`. El motor no se modifica.

## Video de demo

No aplica para esta entrega. La demostración se hace en vivo el día de la sustentación, con la versión en línea o la local.
