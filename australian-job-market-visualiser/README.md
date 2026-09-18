# Australian Job Market Visualiser

A treemap of the Australian labour market, in the spirit of Karpathy's
[US job market visualiser](https://karpathy.ai/jobs/), built on Australian
government data instead of the BLS.

Each rectangle is an occupation. Area is the number of people employed. Colour is
whichever layer you choose: projected growth, skill level, median pay, shortage
status, or a score you generate yourself with a language model.

## Getting real data in

Everything hangs off one spreadsheet.

1. Download **Employment Projections – May 2025 to May 2035.xlsx** from
   <https://www.jobsandskills.gov.au/data/employment-projections>.
2. Look at what's inside before parsing it — sheet names and column headings change
   between annual releases:

   ```
   pip install openpyxl
   python build_data.py "Employment Projections - May 2025 to May 2035.xlsx" --inspect
   ```

3. Build the data file:

   ```
   python build_data.py "Employment Projections - May 2025 to May 2035.xlsx"
   ```

   You should get roughly 350 four-digit occupations covering about 14.7 million
   employed people. If the column guessing goes wrong, `--inspect` shows you the real
   headers and you can adjust `MATCHERS` at the top of the script.

4. Open the viewer. Either serve the folder so it picks up `data.json` automatically:

   ```
   python -m http.server 8000     # then open http://localhost:8000
   ```

   or just open `index.html` and drop `data.json` onto the empty box.

That's the whole thing working, with three layers live: growth to 2030, growth to
2035, and skill level.

## Optional layers

**Median pay and job descriptions** — `python enrich_profiles.py data.json` walks the
JSA occupation profiles and fills in `pay_weekly` and `description`. It caches pages in
`.cache/` and waits a second between requests. The profile pages are Drupal-rendered
and the markup moves around, so treat the extraction patterns in that script as a
starting point rather than something that will keep working forever. If it fights you,
the alternative source is the ABS Employee Earnings and Hours release, which gives
median weekly earnings by ANZSCO and joins on the same codes.

**Shortage status** — the Occupation Shortage List at
<https://www.jobsandskills.gov.au/data/occupation-shortage> ships as a spreadsheet keyed
by occupation code. Set `"shortage": true/false` on each row and the layer lights up.
This is the layer the US version has no equivalent for, and it is probably the most
useful one here.

**A model-scored layer** — this is the part worth playing with:

```
export ANTHROPIC_API_KEY=sk-ant-...
python score_llm.py data.json --prompt prompts/ai_exposure.txt --field ai_exposure
```

`prompts/ai_exposure.txt` is one question. Write another file and you get another
colouring of the same map — offshoring risk, exposure to humanoid robotics, how much
of the work happens outdoors, how much is regulated, whichever question you actually
want to look at. The prompt just has to ask for
`{"score": <number>, "rationale": "..."}`. Scores cache to `scores_<field>.json`, so
re-runs only pay for new rows. Around 350 calls on Haiku is a couple of minutes and a
few cents.

The scoring quality depends heavily on the description text, and Australian occupation
descriptions are much shorter than the BLS handbook entries Karpathy was feeding his
model. Expect noisier scores. Running `enrich_profiles.py` first helps a lot; scoring
at the six-digit level and averaging up to four-digit helps more.

## Notes on the data

- Occupations are keyed by **OSCA**, which replaced ANZSCO as the Australian
  occupation standard. The projections workbook uses four-digit unit groups, about 350
  of them. The profile pages go to six digits, about 1,577 of them. Stay at four digits
  unless you're willing to apportion projections down.
- Employment is reported in thousands and is a **trended** estimate from the ABS Labour
  Force Survey, not a census count. Small occupations are volatile — JSA says as much
  and advises reading growth rates rather than levels for them.
- The projections come from Victoria University's forecasting model and extend existing
  trends. JSA states plainly that they do **not** model the labour market effects of
  generative AI. Whatever the AI-exposure layer shows, the growth layer next to it has
  no AI in it at all. Those two layers disagreeing is the interesting part, not a bug.

## Files

| | |
|---|---|
| `index.html` | the viewer — one file, no build step, no dependencies |
| `build_data.py` | projections workbook → `data.json` |
| `enrich_profiles.py` | adds median pay and descriptions from JSA profiles |
| `score_llm.py` | scores occupations with a model into any field |
| `prompts/ai_exposure.txt` | the example scoring prompt |
