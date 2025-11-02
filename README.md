# 🌞 Solara
### *Season-smart travel insights powered by AI*

Solara blends **LangChain**, **Mixtral**, and **OpenAI ChatGPT** to identify the most popular tourist destinations based on the **time of year**, **historical weather data**, and **popularity trends**.  
It intelligently scores and ranks attractions to help travelers choose where the season truly shines.

---

## 🧭 Features

- 🌤 **Season-aware travel planning**  
  Uses Meteostat weather norms to find the most comfortable months and locations.

- 📊 **Data-driven ranking**  
  Combines weather suitability, tourist popularity, and seasonal interest trends.

- 🧠 **AI-powered insights**  
  Mixtral cleans and structures data, while ChatGPT crafts a narrative summary with travel tips.

- 🗺️ **Flexible data sources**  
  Works with **Google Places**, **Foursquare**, or **SerpAPI** for points of interest.

- ☁️ **Colab-friendly setup**  
  Test instantly in a Google Colab notebook — no local setup required.

---

## 🚀 Quickstart

### 1. Clone and install
```bash
git clone https://github.com/JervisAnthony/Solara.git
cd solara
pip install -r requirements.txt
```

### 2. Add environment variables
Copy the sample env file and fill in your keys:

```bash
cp .env.example .env
```

Inside .env:
```bash
ini

OPENAI_API_KEY=sk-...
TOGETHER_API_KEY=...
# or
MISTRAL_API_KEY=...

GOOGLE_MAPS_API_KEY=...
# or
FOURSQUARE_API_KEY=...
# or
SERPAPI_API_KEY=...
```

3. Run a test query
```bash
make run
# or directly
python -m examples.run_cli
```

📓 Run in Google Colab


Example cell:

```python
!pip -q install git+https://github.com/JervisAnthony/Solara
import os
os.environ["OPENAI_API_KEY"] = "sk-..."
os.environ["GOOGLE_MAPS_API_KEY"] = "..."
os.environ["TOGETHER_API_KEY"] = "..."

from solara.app import app
result = app.invoke({"location_text": "Kyoto, Japan", "month": 11})
print(result["summary"])
```


⚙️ Project Structure
```bash
Solara/
├─ README.md
├─ .env.example
├─ requirements.txt
├─ src/
│  └─ solara/
│     ├─ app.py           # LangGraph orchestrator
│     ├─ config.py        # environment variables
│     ├─ models.py        # Pydantic schemas
│     ├─ nodes/           # core logic: weather, places, scoring, writer
│     └─ utils/
├─ examples/
│  └─ run_cli.py
├─ colab/
│  └─ solara_colab_quickstart.ipynb
└─ tests/
```

🧩 Tech Stack
- LangChain + LangGraph — multi-step pipeline orchestration
- Mixtral-8x7B — extraction and normalization
- OpenAI GPT-4o — reasoning and summary generation
- Meteostat — historical climate data
- Google Maps / Foursquare / SerpAPI — POI data sources
- Python 3.11+

🧠 Example Output
```sql
Top Season Picks for Kyoto in November:

🍁 Fushimi Inari Shrine – cool temperatures and clear skies make it perfect for long hikes.  
🏯 Kiyomizu-dera – maple leaves at full color, excellent visibility for city views.  
🌸 Arashiyama Bamboo Grove – ideal morning lighting and moderate humidity.  
🎨 Kyoto National Museum – great rainy-day option with rich cultural exhibits.
```

🧰 Development

Run tests and lint:
```bash
make test
```

Run locally:
```bash
python -m examples.run_cli
```

🌐 Future Roadmap
- Integrate Google Trends for real seasonal interest signals
- Build FastAPI + Streamlit UI
- Add caching and rate-limit control
- Optional user filters (beach, cultural, adventure)

🪪 License
Released under the MIT License — free for personal and commercial use.

☀️ Author
Jervis Anthony Saldanha

“Discover where the season truly shines.” – Solara
