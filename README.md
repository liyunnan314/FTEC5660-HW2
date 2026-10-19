# FTEC5660 Homework 2: CV Verification Agent

Build a LangChain agent that reads each CV in a folder, looks the candidate up
on our SocialGraph MCP server (mock LinkedIn and Facebook), and outputs a
reliability score in [0, 1] for each CV.

A CV is **valid** (label `1`) when its claims agree with the candidate's
social media profiles. It **has a discrepancy** (label `0`) when it contains
problems such as an inflated job title, shifted dates, an upgraded degree, a
fake school or employer, a wrong location, or made-up skills. Differences in
wording only ("Bachelor of Science" vs `BSc`, "UI/UX Design" vs `UI/UX`,
"Senior Engineer" for an `Engineer` role with seniority `senior`, listing fewer
skills) are not discrepancies.

## Student task

Fill in the two functions in `hw2.py` that contain `### YOUR CODE HERE`. You
may add imports, constants and helper functions above them, but do not change
the provided code below them:

- `build_agent(tools)` creates your agent from the MCP tools.
- `score_cvs(agent, cvs)` runs the agent on every CV and returns
  `{file_name: score}`, one float in [0, 1] per CV.

A score above `0.5` means "valid"; `0.5` or below means "has discrepancy". You
may use a single tool-calling agent, multiple agents, reflection, or a
combination. Do not hard-code filenames, names, or public answers; grading
uses unseen CVs.

## MCP server

The server is hosted at `https://ftec5660.ngrok.app/mcp`. `hw2.py` already
connects to it and passes you these tools:

| Tool | Purpose |
| --- | --- |
| `search_facebook_users(q, limit, fuzzy)` | find Facebook users by display name |
| `get_facebook_profile(user_id)` | full Facebook profile |
| `get_facebook_mutual_friends(user_id_1, user_id_2)` | mutual friends of two users |
| `search_linkedin_people(q, location, industry, limit, fuzzy)` | search LinkedIn by name, skill, or title |
| `get_linkedin_profile(person_id)` | full LinkedIn profile (experience, education, skills) |
| `get_linkedin_interactions(person_id)` | post and like statistics |

Print `tool.name`, `tool.description`, and `tool.args` for the full schemas.

## Setup and public test

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "DEEPSEEK_API_KEY=your_key_here" > .env
python3 hw2.py --cv-folder public_test
```

Use your own DeepSeek API key (from https://platform.deepseek.com).

The program creates `results.csv` in the current directory. Its columns are
`cv`, `score`, and `correctness`. The public labels are in
`public_test/ground_truth.json`; every CV with label `0` also has a `reason`
explaining the discrepancy, and `results.csv` shows it when your agent misses
one. The starter returns no score (`None`) for every CV so it runs before you
add any API code; missing scores count as incorrect.

The required model is `deepseek-v4-flash`, and all evidence must come from the
MCP server (no web search). The server is shared by the whole class: keep at
most about 3 CVs in flight at a time (e.g. `asyncio.Semaphore(3)`). We grade
with our own API key, so never put a key in your code; `.env` must stay out of
git.


## Task 2: Fool the Verifier

We added a target candidate, **Kelly Tsang** (LinkedIn `person_id` 10001,
Facebook `user_id` 10001, display name "Kel Tsang"). Her true CV is
`task2/target_cv.pdf`.

Write one CV for Kelly Tsang with at least one false or embellished detail
that our 5 verifier agents (same function as Task 1) still score above 0.5.
Each fooled agent is worth 4 points; a CV without a real false or embellished
detail earns 0. Attack your own Task 1 agent first:

```bash
cp my_attack.pdf task2/adversarial_cv.pdf
python3 hw2.py --cv-folder task2
```

`results.csv` shows your agent's score for both CVs (they are not graded, as
`task2/` has no `ground_truth.json`). Only the PDF is the attack surface; do not
attack the MCP server. See the homework description for the full rules.

## Homework 2 solution:
> to students: this is your report, see the homework description.

### Task 1

One LangChain `deepseek-v4-flash` tool-calling agent per CV. Almost all of the
logic lives in the system prompt rather than in Python, since the task is really
about teaching the model the rules; `score_cvs` just fans the CVs out with
`asyncio.Semaphore(3)` to stay within the shared MCP server's budget.

Entity resolution turned out to be the hard part, not the comparison. A name on
its own matches hundreds of people, and even adding the country barely helps:
searching "Daniel Wilson" in Germany returns 20 unrelated Daniel Wilsons from
other German cities. Passing the city *and* the industry together is what works.
The CV's headline maps straight onto the industry ("Legal Professional" ->
`Legal`), so `search_linkedin_people("Daniel Wilson", location="Munich",
industry="Legal")` collapses those hundreds down to three. Putting the industry
into `q` instead is actively harmful: such a query has no exact match, the
server falls back to fuzzy matching, and it answers with people from other
countries entirely. So the prompt opens with that one precise query, then pulls
`get_linkedin_profile` on every survivor and anchors on whichever explains the
CV's fingerprint — employers, school, degree, field, skills — discarding anyone
who matches only the name, the city and the skills. Anchoring on the wrong
namesake is the nastiest failure available here, because it invents
discrepancies that are not real and fails CVs that are completely truthful.
Facebook is used only as a tie-breaker, through city, display name or mutual
friends, since it always agrees with LinkedIn.

Once anchored, the agent walks the name, city, jobs, education and skills. The
prompt is explicit that rewording is not lying ("Bachelor of Science" for
`BSc`, "UI/UX Design" for `UI/UX`), and that a seniority that either agrees or
is simply left off is fine while a seniority that contradicts is not: "Senior
Engineer" against LinkedIn `Engineer` + `senior` is acceptable, and so is plain
"Engineer", but "Senior Analyst" against `Analyst` + `junior` is inflated. It
also ignores headlines, hometowns and job descriptions, which by construction
are never where a discrepancy hides. LinkedIn is treated as the record and
Facebook as identity evidence only.

The agent replies with JSON holding the discrepancies it found plus a score. If
that JSON cannot be parsed I fall back to 0.5, and each CV's API call is wrapped
so a single failure cannot sink the whole run.

On `public_test` it scores **7/7**, repeated identically across three
consecutive runs at roughly 40 seconds each. The scores separate cleanly too:
every truthful CV came back at 0.90–0.97 and every falsified one at 0.10, so
nothing lands near the 0.5 boundary where a small wobble would flip a verdict.

### Task 2
> the attack techniques you used and why you expect them to work.
