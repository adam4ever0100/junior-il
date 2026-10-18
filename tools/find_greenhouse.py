"""Verify candidate Greenhouse board tokens for Israeli employers.

Adding a board is cheap — the Greenhouse source already works — but a token
that 404s, returns nothing, or has no Israeli roles is dead weight in the
sample. This checks each candidate against the live API and reports how many
of its open postings look Israeli, so `boards.py` only ever gains boards whose
relevance was measured rather than assumed.

    python tools/find_greenhouse.py wiz.io gong.io similarweb ...

An argument containing a dot is treated as a company domain, and the board
token is extracted from its careers page — guessing tokens from company names
does not work (wiz, gong, hibob and lusha all 404). Anything else is treated as
a token to verify directly.

Prints a ready-to-paste line per board worth adding.
"""
import re
import sys
import time

import httpx

sys.path.insert(0, "ingest")
from junior_il.normalize.location import classify  # noqa: E402

UA = ("junior-il/0.1 (+https://github.com/adam4ever0100/junior-il) "
      "contact: adamabusaad@gmail.com")
API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
PATHS = ("careers", "jobs", "careers/open-positions", "company/careers",
         "about/careers", "careers/all-jobs")

# Every shape a Greenhouse board reference takes in page source.
TOKEN_PATTERNS = (
    re.compile(r"job_board\?for=([a-z0-9_-]{2,40})"),
    re.compile(r"job_board/js\?for=([a-z0-9_-]{2,40})"),
    re.compile(r"boards-api\.greenhouse\.io/v1/boards/([a-z0-9_-]{2,40})"),
    re.compile(r"job-boards\.greenhouse\.io/([a-z0-9_-]{2,40})"),
    re.compile(r"boards\.greenhouse\.io/([a-z0-9_-]{2,40})"),
)
NOT_A_TOKEN = {"embed", "v1", "boards", "js"}


def tokens_from_domain(client: httpx.Client, domain: str) -> list[str]:
    found: list[str] = []
    for path in PATHS:
        for base in (f"https://www.{domain}", f"https://{domain}"):
            try:
                response = client.get(f"{base}/{path}")
            except httpx.HTTPError:
                continue
            if response.status_code != 200:
                continue
            for pattern in TOKEN_PATTERNS:
                for match in pattern.findall(response.text):
                    if match not in NOT_A_TOKEN and match not in found:
                        found.append(match)
            if found:
                return found
        time.sleep(0.3)
    return found


def check(client: httpx.Client, token: str) -> tuple[int, int, str] | None:
    try:
        response = client.get(API.format(token=token))
    except httpx.HTTPError as exc:
        return None if False else (0, 0, f"{type(exc).__name__}")
    if response.status_code != 200:
        return (0, 0, f"http {response.status_code}")
    try:
        jobs = response.json().get("jobs") or []
    except ValueError:
        return (0, 0, "not json")
    israeli = sum(
        1 for job in jobs
        if classify((job.get("location") or {}).get("name") or "")[0]
    )
    company = jobs[0].get("company_name", "") if jobs else ""
    return (len(jobs), israeli, company)


def main(tokens: list[str]) -> int:
    if not tokens:
        print(__doc__)
        return 2
    client = httpx.Client(timeout=20, headers={"User-Agent": UA},
                          follow_redirects=True)
    worth = 0
    candidates: list[str] = []
    for argument in tokens:
        if "." in argument:
            discovered = tokens_from_domain(client, argument)
            if not discovered:
                print(f"    # {argument}: no Greenhouse board in page source",
                      file=sys.stderr)
            candidates.extend(discovered)
        else:
            candidates.append(argument)

    for token in candidates:
        result = check(client, token)
        total, israeli, note = result
        if israeli:
            print(f'    "{token}",'.ljust(28) + f"# {note or token}: {israeli} IL / {total} open")
            worth += 1
        else:
            print(f"    # {token}: {total} open, 0 Israeli ({note})", file=sys.stderr)
        time.sleep(0.6)
    return 0 if worth else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
