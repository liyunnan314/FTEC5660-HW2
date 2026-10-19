#!/usr/bin/env python3
"""FTEC5660 HW2 student starter: build an agent that verifies CVs via MCP."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import re
from pathlib import Path
from typing import Any


MCP_URL = "https://ftec5660.ngrok.app/mcp"
MODEL_NAME = "deepseek-v4-flash"
THRESHOLD = 0.5

MAX_IN_FLIGHT = 3
UNDECIDED = 0.5

VERIFIER_PROMPT = """You are a KYC analyst checking a CV against the candidate's
social profiles. The MCP tools you have are mock LinkedIn and Facebook and they
are your ONLY source of facts. Never use your own knowledge of real companies,
schools or people, and never browse the web. A tool returning no match means
nothing was found, nothing else.

WHAT TO CHECK
Name, current city, every job (employer, title and the seniority its title
implies, start year, end year or Present), every education entry (degree,
school, field, graduation year) and every listed skill.

HOW TO WORK
1. Build a fingerprint from the CV first: full name, current city, every
   employer, every school, every degree and field, every skill, and the years.
2. Identify the person before you judge anything, with one precise query. Make
   your first `search_linkedin_people` call with three arguments at once:
   q = the CV's full name, location = the CV's city (never its country, that
   drags in every namesake nationwide), industry = the CV's headline turned
   into its industry word ("Legal Professional" -> "Legal", "AI Professional" ->
   "AI"). That normally cuts hundreds of namesakes down to two or three. Never
   put the industry or an employer into q: such a query has no exact hit, the
   server falls back to fuzzy matching and answers with unrelated people in
   other countries. Then open `get_linkedin_profile` on each survivor and keep
   whoever explains the fingerprint: employers, school, degree, field, skills.
   Drop anyone who matches only the name, the city and the skills. Anchoring on
   the wrong namesake is the worst failure available here, because it
   manufactures differences that are not real. Only if that first search is
   empty do you widen once: same name and industry without a location, then the
   country instead of the city. Facebook can break a tie through city, display
   name or mutual friends.
3. Once anchored, compare the CV against that profile field by field. LinkedIn
   is the record and Facebook agrees with it, so treat Facebook as identity
   evidence rather than somewhere else to find contradictions.
4. Judge every difference before calling it a discrepancy.

NOT DISCREPANCIES
- Same thing said another way: "Bachelor of Science" for BSc, "Master of
  Business Administration" for MBA, "UI/UX Design" for UI/UX, "Hong Kong" for
  "Hong Kong SAR".
- Anything about seniority that agrees or is simply left out. "Senior Engineer"
  matches a job titled Engineer with seniority senior, and plain "Engineer"
  matches that same job too, because a CV may leave the level unstated. It IS a
  mismatch when the level contradicts the profile, e.g. the CV says "Senior
  Analyst" while LinkedIn says title Analyst, seniority junior.
- Listing fewer skills or fewer jobs than the profile. A CV is allowed to be
  brief; it is not allowed to be false.
- Missing job details, and anything inside job descriptions, headlines or
  hometowns. Ignore those entirely.

DISCREPANCIES
A false claim of any kind: inflated title or seniority, shifted employment or
graduation years, upgraded degree, employer or school that is not there, wrong
city, a skill absent from the profile. One is enough to fail the CV.

SCORE
- 0.85 to 1.0: everything you could check is corroborated.
- 0.6 to 0.8: corroborated, but you are unsure about the identity or a field.
- Around 0.5: you could not find the candidate or could not decide.
- 0.0 to 0.2: at least one claim contradicts the profiles. Use 0.1 when you can
  name the contradiction.

Answer with a single JSON object, no commentary around it:
{"matched_linkedin_id": <int or null>,
 "identity_confidence": <float 0 to 1>,
 "discrepancies": ["Analyst at Microsoft: CV says Senior Analyst, LinkedIn says
Analyst with seniority junior"],
 "notes": "...",
 "score": <float 0 to 1>}"""

CV_PROMPT = """Verify this CV and reply with the JSON object.

<candidate_cv>
{cv_text}
</candidate_cv>"""


def load_env_file(path: Path = Path(".env")) -> None:
    """Load the simple KEY=VALUE entries used by this homework."""
    if not path.is_file():
        return
    import os

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def cv_files(folder: Path) -> list[Path]:
    """Return PDFs directly inside *folder*, sorted numerically (CV_2 before CV_10)."""

    def key(path: Path) -> tuple[int, str]:
        digits = "".join(ch for ch in path.stem if ch.isdigit())
        return (int(digits) if digits else math.inf, path.name)

    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"),
        key=key,
    )


def cv_text(path: Path) -> str:
    """Convert one CV PDF to markdown text."""
    from markitdown import MarkItDown

    return MarkItDown(enable_plugins=False).convert(str(path)).text_content


async def load_mcp_tools() -> list[Any]:
    """Connect to the course MCP server and return its tools as LangChain tools."""
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "social_graph": {
                "transport": "http",
                "url": MCP_URL,
                "headers": {"ngrok-skip-browser-warning": "true"},
            }
        }
    )
    return await client.get_tools()


def build_agent(tools: list[Any]) -> Any:
    """Create and return your agent once.

    ``tools`` are the six SocialGraph MCP tools (Facebook + LinkedIn search and
    profile lookup), already wrapped as LangChain tools. You may add your own
    local tools as well.

    Suggested imports:
        from langchain_deepseek import ChatDeepSeek
        from langchain.agents import create_agent

    Use the DeepSeek model named by ``MODEL_NAME``. The API key is loaded
    from .env.
    """
    from langchain_deepseek import ChatDeepSeek
    from langchain.agents import create_agent

    llm = ChatDeepSeek(
        model=MODEL_NAME,
        temperature=0,
        timeout=180,
        max_retries=3,
    )
    return create_agent(llm, tools, system_prompt=VERIFIER_PROMPT)


async def score_cvs(agent: Any, cvs: dict[str, str]) -> dict[str, float | None]:
    """Run your agent and return one reliability score per CV.

    ``cvs`` maps each file name to its text, e.g. ``{"CV_1.pdf": "...", ...}``.
    Return a float in [0, 1] for every file name: higher means the CV is more
    likely consistent with the candidate's LinkedIn/Facebook data. A score
    above 0.5 counts as "valid", 0.5 or below counts as "has discrepancy".

        {"CV_1.pdf": 0.9, "CV_4.pdf": 0.1, ...}

    Catch errors per CV (e.g. a failed API call) and still return a score for
    it: an exception here means no results.csv, which scores zero.

    MCP tools are async, so call your agent with ``await agent.ainvoke(...)``.
    You may verify CVs in parallel (e.g. ``asyncio.gather``), but keep at most
    about 3 CVs in flight (e.g. with ``asyncio.Semaphore(3)``): the MCP server is
    shared by the whole class.
    """
    slots = asyncio.Semaphore(MAX_IN_FLIGHT)

    async def verify(name: str, cv_text: str) -> tuple[str, float]:
        async with slots:
            payload = CV_PROMPT.format(cv_text=cv_text)
            messages = [{"role": "user", "content": payload}]
            try:
                return name, score_from(await agent.ainvoke({"messages": messages}))
            except Exception:
                return name, UNDECIDED

    scored = await asyncio.gather(*(verify(name, text) for name, text in cvs.items()))
    return dict(scored)


def reply_text(result: Any) -> str:
    """Text of the agent's final answer."""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for message in reversed(messages):
        content = message.get("content") if isinstance(message, dict) else getattr(message, "content", None)
        if isinstance(content, list):
            content = "".join(
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and isinstance(block.get("text"), str)
            )
        if isinstance(content, str) and content.strip():
            return content
    return ""


def score_from(result: Any) -> float:
    """Read the score out of the JSON the agent is asked to reply with."""
    text = reply_text(result)
    try:
        blob = json.loads(text[text.index("{"):text.rindex("}") + 1])
        score = float(blob["score"])
        if 0.0 <= score <= 1.0:
            return score
    except Exception:
        pass
    return UNDECIDED


# Everything below is provided runner/scoring code. No edits are needed.

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def parse_score(value: Any) -> float | None:
    """Accept a float/int, or text containing exactly one number, in [0, 1]."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        score = float(value)
    else:
        text = str(getattr(value, "content", value))
        matches = _NUMBER_RE.findall(text)
        if len(matches) != 1:
            return None
        score = float(matches[0])
    if math.isnan(score) or not 0.0 <= score <= 1.0:
        return None
    return score


def read_ground_truth(folder: Path) -> dict[str, dict[str, Any]]:
    """Read labels (1 = valid CV, 0 = has discrepancy) and reasons from the test folder."""
    path = folder / "ground_truth.json"
    if not path.is_file():
        return {}
    return {
        name: entry if isinstance(entry, dict) else {"label": entry}
        for name, entry in json.loads(path.read_text(encoding="utf-8")).items()
    }


def correctness_text(score: float | None, expected: dict[str, Any] | None) -> str:
    """Return `correct`, or an expected/predicted mismatch explanation."""
    if score is None:
        return "incorrect: score is missing or not a number in [0, 1]"
    if expected is None:
        return "not graded: no ground truth for this CV"
    label = int(expected["label"])
    predicted = 1 if score > THRESHOLD else 0
    if predicted == label:
        return "correct"
    reason = f" ({expected['reason']})" if expected.get("reason") else ""
    return f"incorrect: expected {label}{reason}, predicted {predicted}"


def write_results(names: list[str], scores: dict[str, Any], truth: dict[str, dict[str, Any]]) -> tuple[Path, int]:
    """Write the required results.csv file and return how many CVs were correct."""
    output = Path("results.csv")
    correct = 0
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["cv", "score", "correctness"])
        for name in names:
            score = parse_score(scores.get(name))
            verdict = correctness_text(score, truth.get(name))
            correct += verdict == "correct"
            writer.writerow([name, "" if score is None else f"{score:.4f}", verdict])
    return output, correct


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run FTEC5660 HW2 on CV PDFs")
    parser.add_argument(
        "--cv-folder",
        required=True,
        type=Path,
        help="folder containing CV PDF files",
    )
    return parser.parse_args()


async def run(folder: Path) -> int:
    paths = cv_files(folder)
    if not paths:
        raise SystemExit(f"no PDF files found in {folder}")

    load_env_file()
    cvs = {path.name: cv_text(path) for path in paths}
    tools = await load_mcp_tools()
    agent = build_agent(tools)
    scores = await score_cvs(agent, cvs)
    if not isinstance(scores, dict):
        raise TypeError("score_cvs() must return a dictionary")

    truth = read_ground_truth(folder)
    output, correct = write_results(list(cvs), scores, truth)
    summary = f" Accuracy: {correct}/{len(cvs)}." if truth else ""
    print(f"Processed {len(cvs)} CV(s). Wrote {output}.{summary}")
    return 0


def main() -> int:
    args = parse_args()
    if not args.cv_folder.is_dir():
        raise SystemExit(f"not a folder: {args.cv_folder}")
    return asyncio.run(run(args.cv_folder))


if __name__ == "__main__":
    raise SystemExit(main())
