"""
Gráfica de zonas de decisión: muestra en qué zona cayó el score facial.
Colores accesibles para daltonismo (sin rojo-verde): naranja = rechazo,
gris = zona gris, azul = aprobación. Cada zona lleva su etiqueta escrita,
así no depende solo del color.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from base_conocimiento import UMBRAL_APROBACION, UMBRAL_ZONA_GRIS

COLOR_RECHAZO = "#E69F00"   # naranja (Okabe-Ito)
COLOR_GRIS = "#BDBDBD"
COLOR_APROBADO = "#0072B2"  # azul (Okabe-Ito)


def grafica_zonas(score, anulado_por_fraude=False, score_previo=None):
    """Devuelve una figura con las tres zonas, un marcador en el score y,
    si existe, otro marcador para el score contra el enrolamiento anterior."""
    fig, ax = plt.subplots(figsize=(8, 2.6 if score_previo is not None else 2.2))

    zonas = [
        (0, UMBRAL_ZONA_GRIS, COLOR_RECHAZO, "Rechazo", "#1A1A1A"),
        (UMBRAL_ZONA_GRIS, UMBRAL_APROBACION, COLOR_GRIS, "Zona gris", "#1A1A1A"),
        (UMBRAL_APROBACION, 100, COLOR_APROBADO, "Aprobación", "white"),
    ]
    for inicio, fin, color, etiqueta, color_texto in zonas:
        ax.barh(0, fin - inicio, left=inicio, height=0.6, color=color, edgecolor="white")
        ax.text((inicio + fin) / 2, 0, etiqueta, ha="center", va="center",
                fontsize=10, color=color_texto)

    # Marcador del score
    ax.plot(score, 0.48, marker="v", markersize=14, color="#1A1A1A", clip_on=False)
    texto = f"Score {score:g}"
    if anulado_por_fraude:
        texto += " (anulado por posible fraude)"
    ax.text(score, 0.72, texto, ha="center", va="bottom", fontsize=11,
            fontweight="bold", color="#1A1A1A", clip_on=False)

    # Marcador del score contra el enrolamiento anterior (triángulo debajo de la barra)
    if score_previo is not None:
        ax.plot(score_previo, -0.48, marker="^", markersize=12, color="#555555", clip_on=False)
        ax.text(score_previo, -0.68, f"Enrolamiento anterior {score_previo:g}", ha="center", va="top",
                fontsize=10, color="#333333", clip_on=False)

    ax.set_xlim(0, 100)
    ax.set_ylim(-1.0 if score_previo is not None else -0.4, 1.0)
    ax.set_yticks([])
    ax.set_xticks([0, UMBRAL_ZONA_GRIS, UMBRAL_APROBACION, 100])
    ax.tick_params(axis="x", labelsize=10, colors="#555555")
    ax.set_xlabel("Score (0 a 100)", fontsize=11)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#9E9E9E")
    ax.set_title("Zona de decisión según el score facial", fontsize=13,
                 fontweight="bold", loc="left", pad=28)
    fig.text(0.01, 0.01, "Umbrales de ejemplo del sistema", fontsize=9, color="#757575")
    fig.tight_layout()
    return fig
