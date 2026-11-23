# Demo Guide: Security Posture Lifecycle Cost Tool

A step-by-step script for showing the tool live (in an interview or meeting) or recording a short demo video for GitHub.

Each step lists **Do** (what to click), **Say** (suggested talking points; put them in your own words) and **Check** (what the screen should show, so you know the demo is on track).

All numbers below come from the built-in example scenario. If yours differ, press **File → Load example** to reset.

---

## Choose your demo length

| Version | Time | Steps to use | When |
|---|---|---|---|
| **Short** | ~2 min | 1, 2, 3, 4, 8, 9 | Recorded GIF/video for the README |
| **Standard** | ~5–6 min | 1–11 | Interview screen-share |
| **Full** | ~10 min | 1–13 | Technical deep-dive, or when asked "show me more" |

---

## Before the demo (checklist)

- [ ] Open a terminal in the project folder and activate the project's own environment: `.venv\Scripts\activate`
- [ ] Run `pytest -q` and confirm **14 passed** (you'll show this in Step 12)
- [ ] Start the app: `python -m secposture.gui`
- [ ] Maximize the window. If screen-sharing, share **only the app window**
- [ ] **File → Load example** so all numbers match this guide
- [ ] Close other windows and notifications (Windows: turn on *Do not disturb*)
- [ ] Have `docs/USER_GUIDE.md` and the GitHub repo open in a browser tab
- [ ] Optional: delete old `results.xlsx` / `scenario.json` files from earlier practice runs

---

## Step 1: Introduce the problem (30 s)

**Do:** Stay on **Tab 1 · Inputs**; don't click anything yet.

**Say:**
> "Advanced reactor developers have to show that their physical security is effective *and* affordable. A traditional posture relies on large guard forces, while a security-by-design posture builds protection into the facility so it needs fewer people. I built this tool to compare the full 20-year cost of those choices in today's dollars, and to show how confident we can be in that comparison."

---

## Step 2: Tour the inputs (45 s)

**Do:** Point (move the mouse) to the left panel, then the line-items table.

**Say:**
> "On the left are the financial settings: the discount rate, or WACC, at 7%; a labor wrap rate of 1.8 to turn salaries into full employee cost; maintenance at 3% of purchase price per year; and a 20-year operating life."
>
> "On the right is the baseline facility. C-items are equipment, like fence, vehicle barriers, sensors, cameras and the alarm station. L-items are staff. Each item has a unit cost, a quantity, a lifetime, and the share of its cost that goes to detection, delay or response. For example, a camera is 100% detection and a fence is 100% delay."

**Check:** 12 rows, from `C.1.1 Chain-link fence` to `L.1.3 Security shift supervisor`.

**Mention:** "The cost numbers are illustrative placeholders, not real facility data."

---

## Step 3: Show how cases are defined (45 s)

**Do:** Click **Tab 2 · Case adjustments**.

**Say:**
> "Instead of copying the whole facility for each option, each case only describes how it *differs* from the baseline. There are three cases. Traditional has no changes. Security-by-design has 16 fewer armed responders, but adds 4 ballistic enclosures and 10 cameras. Minimal-consequence represents a facility whose worst-case release is small enough that it needs far fewer responders and no vehicle barrier."

**Do:** Point at `C2 ΔUnits` on row `L.1.1` (**-16**) and on row `C.3.1` (**4**).

**Say:**
> "ΔUnits and ΔLife are added, ×Cost is a multiplier, and ΔMaint changes the maintenance rate. Up to ten cases can be compared."

---

## Step 4: Run and read the results (60 s)

**Do:** Click **Tab 1**, press **▶ Run cases**, then click **Tab 3 · Results**.

**Check:**

| Case | NPV | CAPEX NPV | Labor NPV |
|---|---|---|---|
| Traditional posture | $-87,685,304 | $-3,791,016 | $-83,894,287 |
| Security-by-design | $-65,385,145 | $-4,864,391 | $-60,520,754 |
| Minimal-consequence | $-34,602,666 | $-2,881,443 | $-31,721,223 |

Status bar: *Ran 3 cases. Lowest lifecycle cost: Minimal-consequence ($34.6M NPV).*

**Say (left chart):**
> "This is cumulative cost in today's dollars. All values are spending, so they're negative, and the **highest line is the cheapest**. Security-by-design saves about **$22 million** over 20 years compared with the traditional posture."

**Say (right chart and table):**
> "The bar chart shows *where* the money goes. Response, mostly armed responders, dominates. In the table, labor is about **96%** of the traditional posture's lifecycle cost. Forty responders cost about $5 million a year, so the extra equipment in security-by-design pays for itself easily."

---

## Step 5: Live "what-if" (45 s)

**Do:** **Tab 2** → change `C2 ΔUnits` on row `L.1.1` from **-16** to **-24** → **Tab 1** → **▶ Run cases** → **Tab 3**.

**Check:** Security-by-design NPV changes from **$-65.4M** to about **$-53.7M**.

**Say:**
> "Questions like 'what if the hardened design lets us cut eight more responders?' take seconds to answer. That saves another $11.7 million."

**Do:** Change it back to **-16** and press **▶ Run cases** (or use **File → Load example**).

---

## Step 6: Show a break-even crossing (Standard/Full, 60 s)

**Do:** **Tab 2** → on row `C.3.1` (ballistic enclosure), set `C2 ×Cost` to **15** → **Tab 1** → **▶ Run cases** → **Tab 3**.

**Check:** The orange (Security-by-design) line now **starts lower** than blue (about $-18.4M vs $-9.6M at year 0) and **crosses above it at year 7**. Final NPV is about **$-78.7M**, still cheaper than Traditional's $-87.7M.

**Say:**
> "Here I made the enclosures 15 times more expensive. Security-by-design now costs more up front, but the guard-force savings repay that by **year 7**. That crossing point is the break-even of the security investment, the kind of answer a design team or a regulator wants to see."

**Do:** Set `C2 ×Cost` on `C.3.1` back to **1.0** and press **▶ Run cases** (or **File → Load example**).

---

## Step 7: Model details: replacement buffer and maintenance (Full, 60 s)

**Do:** **Tab 1** → set **Replacement buffer** to **0.50** → **▶ Run cases** → **Tab 3**. Traditional NPV: **$-87,685,304**.

**Do:** **Tab 1** → change **Buffer test** to **> (strict)** → **▶ Run cases** → **Tab 3**.

**Check:** Traditional NPV becomes **$-87,645,875** (about $39,000 less).

**Say:**
> "The radio suite has an 8-year life. Its year-16 replacement leaves exactly 4 years, which equals the buffer threshold of 8 × 0.5. Whether that counts as 'enough time left' depends on using ≥ or >. The reference documentation describes it both ways, so I made it a setting and wrote tests for both."

**Do:** Set **Maintenance profile** to **bathtub** and mention:
> "Maintenance can also follow a bathtub curve, high for new and old equipment, instead of a flat percentage."

**Do:** **File → Load example** to reset.

---

## Step 8: Uncertainty analysis (60 s)

**Do:** Click **Tab 4 · Uncertainty** → **Samples** = 500 → **Run uncertainty analysis** (takes a few seconds).

**Check (left chart):** three median lines with shaded bands. At year 20, roughly:

| Case | P10 | P50 | P90 |
|---|---|---|---|
| Traditional | $-101M | $-89M | $-77M |
| Security-by-design | $-76M | $-66M | $-58M |
| Minimal-consequence | $-41M | $-35M | $-31M |

**Say:**
> "Cost estimates are never exact. Each case is rerun 500 times while the discount rate, equipment costs (skewed toward overruns), salaries, maintenance and equipment lifetimes vary. The line is the median, and the band covers 80% of outcomes. The bands **barely touch**, so even with these uncertainties security-by-design stays cheaper than the traditional posture. A single deterministic spreadsheet can't tell you that."

---

## Step 9: Sensitivity (tornado) (30 s)

**Check (right chart):** top bars are **L.1.1 Armed responder** (±$11.7M) and **WACC** (about −$9.3M / +$7.8M); equipment bars are tiny.

**Say:**
> "The tornado chart changes each input by 20% and ranks them by effect. Responder cost and the discount rate dominate, and individual equipment prices barely matter. So better data effort should go into staffing estimates, not camera prices."

---

## Step 10: Export to Excel (45 s)

**Do:** **File → Export results to Excel…** → save as `results.xlsx` → open it in Excel.

**Check and show:**
- **Summary** sheet: same NPVs as Tab 3.
- **CNPV** sheet: year-by-year values with a native Excel chart.
- **Traditional posture** sheet → row `C.2.2 Assessment camera`: **$240,000** in years **0, 7 and 14**, and **$7,200** maintenance in every other year.

**Say:**
> "Results export to Excel for people who live in spreadsheets, including a year-by-year audit trail. You can see the cameras' 7-year lifetime here: replaced at years 7 and 14, maintenance otherwise."

---

## Step 11: Save and reload a scenario (20 s)

**Do:** **File → Save scenario…** → `my_scenario.json`. Then **File → Open scenario…** → pick it.

**Say:**
> "Scenarios are saved as plain JSON, so they can be version-controlled, shared, or generated by scripts."

---

## Step 12: Tests and code quality (Full, 60 s)

**Do:** Switch to the terminal:
```bat
pytest -q
```
**Check:** `14 passed`.

**Say:**
> "The calculation engine is plain Python and NumPy, separate from the GUI, with 14 unit tests. They reproduce the documented replacement examples, check discounting and wrap rates, and confirm that detection, delay and response always add up to the total. GitHub Actions runs them on every push."

**Optional:** open `secposture/engine.py` and show `is_replacement_year()`, which is short and readable.

---

## Step 13: Command line and wrap-up (Full, 45 s)

**Do:**
```bat
python -m secposture.cli --out results
```
**Check:** a summary table plus P10/P50/P90 lines; the `results` folder has 4 PNG charts, `results.xlsx` and `cnpv.csv`.

**Say (closing):**
> "The same engine runs headless, so it can be batch-run or plugged into other analyses. Next I'd add financing schedules, climate-driven maintenance, which ties to my meteorology background, and a cost-versus-effectiveness view that pairs each posture with an adversary-path model such as EASI. Then the question becomes not only *what does it cost* but *how much protection does each dollar buy*."

---

## Recording the demo for GitHub

**Tools (Windows):**
- **ScreenToGif** (free, screentogif.com): records a window straight to GIF. Best for a short README demo.
- **Xbox Game Bar** (built in): press **Win + G** → record (MP4).
- **OBS Studio** (free): for a narrated video.

**Tips:**
1. Record the **Short** version (Steps 1–4, 8, 9) without talking. Aim for **under 60 seconds** and **under 10 MB**.
2. Pause about 1 second on each result so viewers can read it.
3. Save as `docs/demo.gif`, then add this near the top of `README.md`:
   ```markdown
   ![Demo](docs/demo.gif)
   ```
4. For a narrated version (2–3 min), upload to YouTube as *Unlisted* and link it in the README and on your resume.
5. Commit and push:
   ```bat
   git add docs/demo.gif README.md docs/DEMO_GUIDE.md
   git commit -m "Add demo"
   git push
   ```

---

## If something goes wrong during a live demo

| Situation | Recovery |
|---|---|
| Numbers don't match this guide | **File → Load example**, then **▶ Run cases** |
| "Invalid line item" or "Invalid adjustment" pop-up | You typed text or a typo into a number cell; fix the cell (for example `8000`, not `$8,000`) |
| Chart didn't change | Press **▶ Run cases**; results only update when you run |
| Uncertainty is slow | Lower **Samples** to 200 |
| App froze or closed | Re-run `python -m secposture.gui`; it starts with the example loaded |

Say calmly: *"Let me reset to the example,"* and carry on. Recovering smoothly also leaves a good impression.

---

## Likely questions and suggested answers

**Why Python instead of Excel?**
> "Excel works well for transparency, but Python made it easy to add things that are hard in a spreadsheet: Monte Carlo over hundreds of runs, unit tests, version control, and a reusable engine with both a GUI and a command line. I kept Excel export, so results still go to spreadsheet users."

**How do you know the numbers are right?**
> "The tests reproduce the documented worked examples, check edge cases like the buffer tie, and verify that capital plus labor and detection plus delay plus response both equal the total. The Excel export also shows every item's cost in every year, so it can be audited."

**Why are the NPVs negative?**
> "The model only counts spending, so a higher, closer-to-zero line means cheaper."

**Where did the cost data come from?**
> "These are illustrative placeholders to demonstrate the method. With real facility data from the team, the same workflow applies."

**What are the limitations?**
> "It measures cost, not effectiveness. Purchases are cash-only, prices are constant, and maintenance is a percentage of capital cost. The uncertainty ranges are fixed in this version. Each of these is on the roadmap."

**What would you do next if you joined the team?**
> "Learn how the team uses its current cost model, then add the features users ask for most, like result export, financing and non-flat maintenance, plus uncertainty and sensitivity analysis to support design decisions."

**Why does uncertainty matter here?**
> "Decisions between postures are made early, when costs are least certain. Showing whether the ranking holds across plausible ranges is more useful than a single number."
