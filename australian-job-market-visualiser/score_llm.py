#!/usr/bin/env python3
"""
Score every occupation in data.json with a language model and write the result
into a field the viewer can colour by.

    export ANTHROPIC_API_KEY=sk-ant-...
    python score_llm.py data.json --prompt prompts/ai_exposure.txt --field ai_exposure

Write your own prompt file to get a different layer — offshoring risk, exposure to
robotics, how much of the work is outdoors, whatever you want to look at. The prompt
must ask for JSON of the form {"score": <number>, "rationale": "<a sentence or two>"}.

Scores are cached in scores_<field>.json, so a re-run only pays for new occupations.
About 350 calls on Haiku costs cents and takes a couple of minutes.
"""

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request

API = "https://api.anthropic.com/v1/messages"


def call(model, system, user, key, max_tokens=400):
    body = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "content-type": "application/json",
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.load(r)
    return "".join(b.get("text", "") for b in data.get("content", []))


def parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON in reply")
    return json.loads(m.group(0))


def describe(d):
    bits = [f"Occupation: {d['name']} (OSCA {d['code']})",
            f"Occupation group: {d.get('major_name')}"]
    if d.get("skill_level"):
        bits.append(f"Skill level: {d['skill_level']} (1 = bachelor degree or higher, "
                    f"5 = certificate I or secondary school)")
    if d.get("emp_2025"):
        bits.append(f"People employed in Australia: {d['emp_2025']:,}")
    if d.get("pay_weekly"):
        bits.append(f"Median weekly earnings: ${d['pay_weekly']:,}")
    if d.get("description"):
        bits.append(f"\nWhat the job involves:\n{d['description']}")
    return "\n".join(bits)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="?", default="data.json")
    ap.add_argument("--prompt", default="prompts/ai_exposure.txt")
    ap.add_argument("--field", default="ai_exposure")
    ap.add_argument("--model", default="claude-haiku-4-5-20251001")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("set ANTHROPIC_API_KEY")

    system = open(args.prompt, encoding="utf-8").read()
    doc = json.load(open(args.data))
    cache_path = f"scores_{args.field}.json"
    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}

    todo = [d for d in doc["occupations"] if d["code"] not in cache]
    print(f"{len(cache)} cached, {len(todo)} to score with {args.model}")

    def work(d):
        try:
            obj = parse_json(call(args.model, system, describe(d), key))
            score = obj.get("score", obj.get("exposure"))
            return d["code"], {"score": float(score),
                               "rationale": str(obj.get("rationale", ""))[:400]}
        except Exception as e:
            return d["code"], {"error": str(e)}

    done = 0
    with cf.ThreadPoolExecutor(args.workers) as pool:
        for code, res in pool.map(work, todo):
            cache[code] = res
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(todo)}")
                json.dump(cache, open(cache_path, "w"), indent=1)
    json.dump(cache, open(cache_path, "w"), indent=1)

    # The viewer shows d.ai_rationale under the tooltip for the AI layer.
    rationale_field = "ai_rationale" if args.field == "ai_exposure" else args.field + "_rationale"
    ok = 0
    for d in doc["occupations"]:
        r = cache.get(d["code"], {})
        if "score" in r:
            d[args.field] = r["score"]
            d[rationale_field] = r["rationale"]
            ok += 1
    json.dump(doc, open(args.data, "w"), indent=1)
    print(f"\nscored {ok}/{len(doc['occupations'])} into '{args.field}' in {args.data}")


if __name__ == "__main__":
    main()
