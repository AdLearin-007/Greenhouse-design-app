# Greenhouse System Planner (Python)

A website that builds a 3D greenhouse from your choices: structure style,
growing system (traditional, hydroponic or aquaponic), size, glazing and
equipment. It lays out every component, traces the water loop, and works out
the engineering numbers.

## Run it

You need Python 3.9 or newer.

```bash
cd greenhouse_planner
pip install -r requirements.txt
streamlit run app.py
```

Your browser opens at http://localhost:8501. Change anything in the sidebar
and the model rebuilds.

## How the code is organized

| File | What it does |
| --- | --- |
| `planner.py` | All the planning logic, in plain Python with no extra packages. Cross-section profiles for each style, the floor layout, every component's geometry, water-flow paths, and the numbers (volume, fans, water, fish stocking). |
| `app.py` | The website. Streamlit makes the sidebar controls and page; Plotly draws the 3D model from the data `planner.py` returns. |

Because the logic is separate from the website, you can use `planner.py` on
its own, for example in a notebook:

```python
from planner import Settings, build
model = build(Settings(style="venlo", system="hydro", hydro="dwc", width=12, length=24))
print(model.stats["plant_sites"], model.stats["water_l"])
```

## Engineering assumptions (edit them at the top of planner.py)

- Ventilation: one air change per minute; a 36-inch fan moves about 283 m³/min.
- Shade cloth: 40%, so 60% of light passes.
- Aquaponics: 60 g of fish feed per m² of grow bed per day, fish eat 1.5% of
  body weight daily, tanks stocked at 20 kg of fish per m³.
- Plant spacing: lettuce 30 cm in soil, 20 cm in NFT and rafts; tomatoes 50 cm.

## Ideas to extend it

- Add a heating calculation from glazing area and a winter design temperature.
- Export a parts list (pipe length, number of channels, rafts) to CSV.
- Add your own crop list with spacing and yield per plant to estimate harvest.
