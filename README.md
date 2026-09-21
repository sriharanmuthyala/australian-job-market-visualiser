# Where Australia Works

An interactive visualisation of the Australian labour market built from Jobs and Skills Australia (JSA) and ABS data.

The project explores roughly 350 four-digit ANZSCO occupation groups. Rectangle size represents current employment and colour can be switched between projected growth, median weekly earnings, skill level, occupation group and an experimental AI task-exposure score.

Live site: https://sriharanmuthyala.github.io/australian-job-market-visualiser/

## What the dashboard includes

- Employment baseline for May 2025
- JSA employment projections to 2030 and 2035
- Median weekly earnings
- ANZSCO skill level
- Occupation-group view
- Experimental AI task-exposure layer
- Search and filters for occupation, group, skill level, outlook and workforce size
- Interactive occupation detail panel
- Jobs by occupation group
- Top projected job gains to 2035
- Biggest projected movers
- Direct links to Jobs and Skills Australia occupation profiles

## Primary data sources

### Employment and projections

Jobs and Skills Australia  
**Employment Projections - May 2025 to May 2035**

https://www.jobsandskills.gov.au/data/employment-projections

The starting employment estimate is JSA Labour Force Trend data for May 2025. JSA describes the projections as indicative future trends based on current assumptions rather than precise forecasts. JSA also notes that these projections do not currently incorporate the labour-market effects of generative AI.

### Median weekly earnings

Jobs and Skills Australia occupation profiles, based on ABS Employee Earnings and Hours.

Current JSA ANZSCO occupation profiles use **May 2025** earnings data:

https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles

The dashboard currently uses an interim profile extract with a **May 2023 earnings reference period** for 278 of the 358 occupations. Updating the live dataset to the May 2025 earnings release is one of the remaining data-refresh tasks.

### Occupation shortage

Jobs and Skills Australia  
**2025 Occupation Shortage List**

https://www.jobsandskills.gov.au/data/occupation-shortage

JSA publishes a four-digit ANZSCO Unit Group Shortage List. The repository now includes `enrich_shortage.py` so that official shortage ratings can be merged into `data.json`. Once populated, the shortage colour layer appears automatically in the dashboard.

## Build the employment dataset

Download:

**Employment Projections - May 2025 to May 2035.xlsx**

Then inspect the workbook:

```bash
pip install openpyxl
python build_data.py "Employment Projections - May 2025 to May 2035.xlsx" --inspect
```

Build `data.json`:

```bash
python build_data.py "Employment Projections - May 2025 to May 2035.xlsx"
```

Serve the project locally:

```bash
python -m http.server 8000
```

Then open:

`http://localhost:8000`

## Refresh median weekly earnings

The repository contains `enrich_pay.py`, which is designed to merge the current JSA ANZSCO occupation-profile workbook into `data.json`.

The current JSA downloadable ANZSCO occupation data is the February 2026 release and includes May 2025 Employee Earnings and Hours data.

If the automated JSA download is unavailable, download the workbook manually from:

https://www.jobsandskills.gov.au/data/occupation-and-industry-profiles

and run the enrichment script locally.

## Add the 2025 shortage layer

Download:

**2025 Unit Group Shortage List - 4 digit ANZSCO.xlsx**

from:

https://www.jobsandskills.gov.au/data/occupation-shortage

Then run:

```bash
python enrich_shortage.py data.json "2025 Unit Group Shortage List - 4 digit ANZSCO.xlsx"
```

The script preserves the original national rating and adds a simple Boolean shortage field for the visual layer.

## AI task-exposure methodology

The AI layer is experimental. It is intended to estimate **task exposure to AI**, not redundancy risk, job-loss probability or future employment.

The current live scores were generated using the original prompt:

`prompts/ai_exposure.txt`

A more balanced second-generation methodology has now been prepared:

`prompts/ai_task_exposure_v2.txt`

The v2 prompt explicitly considers:

- automation and augmentation
- physical and embodied work
- human relationships and trust
- professional accountability
- regulation and licensing
- safety and privacy
- contextual and tacit knowledge
- productivity effects
- the distinction between task transformation and employment demand

The live scores should only be replaced after the full occupation set is rescored. To do that:

```bash
export ANTHROPIC_API_KEY=...
python score_llm.py data.json \
  --prompt prompts/ai_task_exposure_v2.txt \
  --field ai_exposure \
  --force
```

The `--force` option deliberately ignores the previous score cache and rescores every occupation.

## Important interpretation notes

- A large rectangle means more people are employed in that occupation.
- A strong growth colour means higher projected employment growth, not necessarily easier recruitment.
- An occupation in shortage can still be competitive for jobseekers.
- A high AI task-exposure score does **not** mean the occupation is predicted to disappear.
- Small occupations can have volatile employment estimates, so growth rates should be interpreted with care.
- The employment projections and the AI layer are independent: JSA states that its current projections do not incorporate generative-AI labour-market effects.

## Repository structure

| File | Purpose |
|---|---|
| `index.html` | Complete interactive dashboard |
| `data.json` | Current labour-market dataset used by the site |
| `build_data.py` | Builds projection data from the JSA workbook |
| `enrich_pay.py` | Refreshes median weekly earnings from JSA occupation data |
| `enrich_profiles.py` | Earlier JSA profile enrichment utility |
| `enrich_shortage.py` | Adds the official 2025 four-digit shortage layer |
| `score_llm.py` | Model-scoring pipeline |
| `prompts/ai_exposure.txt` | Prompt used for the current live AI scores |
| `prompts/ai_task_exposure_v2.txt` | Balanced next-generation AI task-exposure prompt |

## Remaining v1 data work

The interface is substantially complete. The remaining work is primarily data quality rather than additional UI:

1. Refresh the pay layer from the May 2023 interim extract to the current May 2025 earnings data.
2. Run `enrich_shortage.py` with the official 2025 four-digit OSL workbook.
3. Rescore all occupations with the v2 AI task-exposure methodology.
4. Recheck the merged dataset and source metadata before calling the release v1.0.

## Inspiration

The initial treemap concept was inspired by Andrej Karpathy's US Job Market Visualizer:

https://karpathy.ai/jobs/

The Australian implementation, data model, filters, source framing, charts and interaction design have been adapted for Australian labour-market data.

Built by **Sri Muthyala**.
