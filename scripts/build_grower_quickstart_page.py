"""Build a standalone grower quickstart HTML file for the F3 submission."""

from __future__ import annotations

import argparse
import base64
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIGURES_DIR = ROOT / "submission" / "figures"
DEFAULT_OUTPUT = ROOT / "submission" / "grower_quickstart.html"


def image_data_uri(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing image asset: {path}")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_html(figures_dir: Path) -> str:
    overview = image_data_uri(figures_dir / "spatial_zone_maps.png")
    partner = image_data_uri(figures_dir / "partner_site_1_report_zone_map.png")
    overlay = image_data_uri(figures_dir / "partner_site_1_canopy_priority_overlay.png")
    title = "Persistent Orchard Underperformance Mapper - Grower Quickstart"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #5f6b7a;
      --line: #cbd5df;
      --paper: #f7f8f4;
      --panel: #ffffff;
      --green: #1a7f37;
      --red: #b42318;
      --orange: #b86100;
      --blue: #235789;
    }}
    * {{ box-sizing: border-box; }}
    html {{
      width: 100%;
      overflow-x: hidden;
    }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: var(--ink);
      background: var(--paper);
      line-height: 1.45;
      width: 100%;
      overflow-x: hidden;
    }}
    header > div,
    main,
    section,
    .band,
    .node,
    .legend-item,
    .owner,
    .brief,
    .brief li {{
      min-width: 0;
    }}
    h1, h2, h3, p, li, figcaption {{
      overflow-wrap: break-word;
    }}
    header {{
      padding: 22px 28px 14px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 16px;
      align-items: end;
    }}
    h1 {{
      margin: 0;
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 12px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    h3 {{
      margin: 0 0 6px;
      font-size: 14px;
      letter-spacing: 0;
    }}
    p {{ margin: 0 0 10px; }}
    .subhead {{
      margin-top: 8px;
      max-width: 860px;
      color: var(--muted);
      font-size: 14px;
    }}
    .lang-toggle {{
      display: inline-flex;
      border: 1px solid var(--line);
      border-radius: 6px;
      overflow: hidden;
      background: #ffffff;
      min-width: 128px;
    }}
    .lang-toggle button {{
      border: 0;
      background: transparent;
      color: var(--ink);
      padding: 9px 14px;
      min-width: 64px;
      font-size: 13px;
      cursor: pointer;
    }}
    .lang-toggle button.active {{
      background: var(--blue);
      color: #ffffff;
    }}
    main {{
      padding: 18px 28px 30px;
      display: grid;
      gap: 18px;
    }}
    .top-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.05fr) minmax(320px, .95fr);
      gap: 18px;
      align-items: stretch;
    }}
    .band {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .brief {{
      display: grid;
      gap: 8px;
      padding-left: 0;
      list-style: none;
      margin: 0;
    }}
    .brief li {{
      border-left: 4px solid var(--blue);
      padding: 7px 10px;
      background: #f4f7fb;
      min-height: 36px;
    }}
    .legend {{
      display: grid;
      grid-template-columns: repeat(4, minmax(130px, 1fr));
      gap: 10px;
    }}
    .legend-item {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #ffffff;
      min-height: 88px;
    }}
    .swatch {{
      width: 34px;
      height: 8px;
      border-radius: 2px;
      margin-bottom: 8px;
    }}
    .swatch.red {{ background: var(--red); }}
    .swatch.orange {{ background: #f79009; }}
    .swatch.pale {{ background: #a6c8a0; }}
    .swatch.green {{ background: var(--green); }}
    .decision {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .node {{
      border: 1px solid var(--line);
      border-top: 5px solid var(--blue);
      border-radius: 8px;
      padding: 12px;
      background: #ffffff;
      min-height: 132px;
    }}
    .node.action {{ border-top-color: var(--red); }}
    .node.record {{ border-top-color: var(--green); }}
    .node.wait {{ border-top-color: var(--orange); }}
    .media-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 14px;
    }}
    figure {{
      margin: 0;
      display: grid;
      gap: 8px;
    }}
    img {{
      display: block;
      width: 100%;
      max-height: 520px;
      object-fit: contain;
      background: #eef2f0;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    figcaption {{
      color: var(--muted);
      font-size: 12px;
    }}
    .owners {{
      display: grid;
      grid-template-columns: repeat(4, minmax(150px, 1fr));
      gap: 10px;
    }}
    .owner {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: #ffffff;
      min-height: 104px;
    }}
    [data-lang="es"] {{ display: none; }}
    body.show-es [data-lang="en"] {{ display: none; }}
    body.show-es [data-lang="es"] {{ display: block; }}
    body.show-es .grid-lang[data-lang="es"] {{ display: grid; }}
    .grid-lang[data-lang="es"] {{ display: none; }}
    @media (max-width: 900px) {{
      header, main {{ padding-left: 16px; padding-right: 16px; }}
      header {{ grid-template-columns: 1fr; }}
      .top-grid, .media-grid, .decision, .legend, .owners {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 24px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Persistent Orchard Underperformance Mapper</h1>
      <p class="subhead" data-lang="en">One-page field quickstart for turning the final F3 orchard stress maps into a scoutable work order without making a diagnosis from satellite imagery alone.</p>
      <p class="subhead" data-lang="es">Guia breve de campo para convertir los mapas finales de F3 en una lista de exploracion sin diagnosticar una causa solo con imagenes satelitales.</p>
    </div>
    <div class="lang-toggle" aria-label="Language">
      <button type="button" class="active" data-set-lang="en">EN</button>
      <button type="button" data-set-lang="es">ES</button>
    </div>
  </header>

  <main>
    <section class="top-grid">
      <div class="band">
        <h2 data-lang="en">Practical Example Field Brief</h2>
        <h2 data-lang="es">Resumen Practico De Campo</h2>
        <ol class="brief" data-lang="en">
          <li>This map only tells us where canopy repeatedly looked weaker than the same site's baseline.</li>
          <li>Start with the Scout first coordinate and compare it with a nearby Strong reference area.</li>
          <li>In the field, check visible canopy, irrigation distribution, pest/disease symptoms, soil or water movement, and recent records.</li>
          <li>Send findings, photos, and notes to the farm manager, PCA/crop advisor, or irrigation lead depending on what is observed.</li>
          <li>Record confirmed concern, known context, no action, or revisit later so the next model run can learn from field reality.</li>
        </ol>
        <ol class="brief" data-lang="es">
          <li>Este mapa solo indica donde el dosel se vio repetidamente mas debil que la linea base del mismo sitio.</li>
          <li>Empiece con la coordenada de Explorar primero y comparela con una zona cercana de Referencia fuerte.</li>
          <li>En el campo, revise el dosel visible, la distribucion del riego, sintomas de plagas o enfermedad, movimiento de suelo o agua, y registros recientes.</li>
          <li>Envie hallazgos, fotos y notas al encargado del rancho, asesor agricola/PCA, o responsable de riego segun lo observado.</li>
          <li>Registre problema confirmado, contexto conocido, sin accion, o revisar despues para que la siguiente corrida del modelo aprenda de la realidad del campo.</li>
        </ol>
      </div>

      <div class="band">
        <h2 data-lang="en">Zone Classes</h2>
        <h2 data-lang="es">Clases Del Mapa</h2>
        <div class="legend">
          <div class="legend-item"><div class="swatch red"></div><h3 data-lang="en">Scout first</h3><h3 data-lang="es">Explorar primero</h3><p data-lang="en">Visit first. Repeated weaker canopy signal inside eligible canopy.</p><p data-lang="es">Visitar primero. Senal debil repetida dentro del dosel elegible.</p></div>
          <div class="legend-item"><div class="swatch orange"></div><h3>Monitor</h3><p data-lang="en">Check if nearby or if field time allows.</p><p data-lang="es">Revisar si esta cerca o si hay tiempo de campo.</p></div>
          <div class="legend-item"><div class="swatch pale"></div><h3>Stable</h3><p data-lang="en">Use as normal context. No action from this signal alone.</p><p data-lang="es">Usar como contexto normal. Sin accion solo por esta senal.</p></div>
          <div class="legend-item"><div class="swatch green"></div><h3 data-lang="en">Strong reference</h3><h3 data-lang="es">Referencia fuerte</h3><p data-lang="en">Compare against this stronger within-site canopy.</p><p data-lang="es">Comparar contra este dosel mas fuerte dentro del mismo sitio.</p></div>
        </div>
      </div>
    </section>

    <section class="band">
      <h2 data-lang="en">Decision Tree</h2>
      <h2 data-lang="es">Arbol De Decision</h2>
      <div class="decision">
        <div class="node action"><h3 data-lang="en">1. Where to look</h3><h3 data-lang="es">1. Donde mirar</h3><p data-lang="en">Open the map and scouting table. Send a scout to the highest-ranked Scout first centroid before Monitor zones.</p><p data-lang="es">Abra el mapa y la tabla. Mande a una persona a la coordenada mas alta de Explorar primero antes de zonas Monitor.</p></div>
        <div class="node"><h3 data-lang="en">2. What to compare</h3><h3 data-lang="es">2. Que comparar</h3><p data-lang="en">Compare the zone against a nearby Strong reference area so the decision stays local to the same site.</p><p data-lang="es">Compare la zona con una Referencia fuerte cercana para mantener la decision dentro del mismo sitio.</p></div>
        <div class="node"><h3 data-lang="en">3. What to check</h3><h3 data-lang="es">3. Que revisar</h3><p data-lang="en">Look at canopy, irrigation distribution, pest/disease symptoms, soil or water movement, field memory, and records.</p><p data-lang="es">Revise dosel, distribucion de riego, sintomas de plagas o enfermedad, suelo o agua, memoria de campo y registros.</p></div>
        <div class="node record"><h3 data-lang="en">4. Who receives it</h3><h3 data-lang="es">4. A quien enviarlo</h3><p data-lang="en">Farm manager gets the worklist; PCA/crop advisor gets crop symptoms; irrigation lead gets distribution concerns.</p><p data-lang="es">El encargado recibe la lista; el asesor/PCA recibe sintomas del cultivo; riego recibe problemas de distribucion.</p></div>
        <div class="node record"><h3 data-lang="en">5. What to record</h3><h3 data-lang="es">5. Que registrar</h3><p data-lang="en">Use confirmed concern, known context, no action, or revisit later. Attach photos and records checked.</p><p data-lang="es">Use problema confirmado, contexto conocido, sin accion, o revisar despues. Agregue fotos y registros revisados.</p></div>
        <div class="node wait"><h3 data-lang="en">6. How the model improves</h3><h3 data-lang="es">6. Como mejora el modelo</h3><p data-lang="en">Confirmed zones keep trust; known-context and no-action zones lower future false alerts; missed signals tune the mask.</p><p data-lang="es">Zonas confirmadas mantienen confianza; contexto conocido y sin accion reducen falsas alertas; senales perdidas ajustan la mascara.</p></div>
      </div>
    </section>

    <section class="band">
      <h2 data-lang="en">Who Gets Which Output</h2>
      <h2 data-lang="es">Quien Recibe Cada Salida</h2>
      <div class="owners">
        <div class="owner"><h3 data-lang="en">Farm manager</h3><h3 data-lang="es">Encargado</h3><p data-lang="en">PDF, work-order CSV, and first three Scout first locations.</p><p data-lang="es">PDF, CSV de trabajo, y primeras tres ubicaciones de Explorar primero.</p></div>
        <div class="owner"><h3 data-lang="en">PCA / crop advisor</h3><h3 data-lang="es">Asesor / PCA</h3><p data-lang="en">Zone map, photos, canopy notes, pest/disease observations, and records checked.</p><p data-lang="es">Mapa de zonas, fotos, notas del dosel, observaciones de plagas/enfermedad y registros revisados.</p></div>
        <div class="owner"><h3 data-lang="en">Irrigation lead</h3><h3 data-lang="es">Responsable de riego</h3><p data-lang="en">Only receive zones where field notes show distribution, pressure, wet/dry, or water-movement concerns.</p><p data-lang="es">Solo recibe zonas donde el campo muestra distribucion, presion, seco/mojado, o movimiento de agua.</p></div>
        <div class="owner"><h3 data-lang="en">Data owner</h3><h3 data-lang="es">Responsable de datos</h3><p data-lang="en">Receives feedback rows so the next run can recalibrate thresholds and masks.</p><p data-lang="es">Recibe filas de retroalimentacion para recalibrar umbrales y mascaras en la proxima corrida.</p></div>
      </div>
    </section>

    <section class="media-grid">
      <figure class="band">
        <img src="{overview}" alt="Six-site scouting-priority overview map">
        <figcaption data-lang="en">Six-site output overview. Use it to choose the site and then open the detailed map.</figcaption>
        <figcaption data-lang="es">Resumen de seis sitios. Uselo para escoger el sitio y luego abrir el mapa detallado.</figcaption>
      </figure>
      <figure class="band">
        <img src="{partner}" alt="Partner site scouting-priority map">
        <figcaption data-lang="en">Partner site detail. Start with red Scout first zones, then compare with green Strong reference zones.</figcaption>
        <figcaption data-lang="es">Detalle del sitio socio. Empiece con rojo Explorar primero y compare con verde Referencia fuerte.</figcaption>
      </figure>
    </section>

    <section class="band">
      <h2 data-lang="en">Canopy Guardrail</h2>
      <h2 data-lang="es">Control Del Dosel</h2>
      <figure>
        <img src="{overlay}" alt="Partner site canopy and priority overlay">
        <figcaption data-lang="en">Priority colors are clipped to eligible canopy before scoring, which reduces road, canal, bare-ground, water, and field-margin false alerts.</figcaption>
        <figcaption data-lang="es">Los colores de prioridad se limitan al dosel elegible antes de puntuar, reduciendo alertas en caminos, canales, suelo desnudo, agua y bordes.</figcaption>
      </figure>
    </section>
  </main>

  <script>
    const buttons = document.querySelectorAll('[data-set-lang]');
    buttons.forEach((button) => {{
      button.addEventListener('click', () => {{
        const lang = button.getAttribute('data-set-lang');
        document.body.classList.toggle('show-es', lang === 'es');
        buttons.forEach((b) => b.classList.toggle('active', b === button));
        document.documentElement.lang = lang || 'en';
      }});
    }});
  </script>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--figures-dir", type=Path, default=DEFAULT_FIGURES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(args.figures_dir), encoding="utf-8", newline="\n")
    print(f"Built grower quickstart page: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
