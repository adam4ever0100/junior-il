"""Find the Comeet board behind a company's careers page.

Comeet boards need two identifiers — a company uid like "A8.00D" and a public
token — and both are embedded in the company's own careers page, because the
page's JavaScript calls the same API this project calls. This script extracts
them so a new board can be added to `junior_il/boards.py` with its identifiers
verified rather than guessed.

    python tools/find_comeet.py cycode.com firebolt.io ...

Prints a ready-to-paste line for each board it can verify against the live API.
"""
import re
import sys
import time

import httpx

UA = ("junior-il/0.1 (+https://github.com/adam4ever0100/junior-il) "
      "contact: adamabusaad@gmail.com")
PATHS = ("careers", "jobs", "careers/open-positions", "company/careers",
         "about/careers", "careers/jobs")
API = "https://www.comeet.co/careers-api/2.0/company/{uid}/positions"

# Both appear in page source, often backslash-escaped inside inline JSON. The
# `comeet_uid` / `comeet_token` pair is the Comeet WordPress plugin, which is
# how a lot of mid-size Israeli companies run their careers page — and the only
# shape that carries both identifiers in one place.
UID = re.compile(r"company\\?/([A-Z0-9]{2}\.[0-9A-F]{3})"
                 r"|comeet_uid\"?:\s*\"([A-Z0-9]{2}\.[0-9A-F]{3})")
TOKEN = re.compile(r"token=([0-9A-F]{24,48})"
                   r"|comeet_token\"?:\s*\"([0-9A-F]{24,48})")
HOSTED = re.compile(r"comeet\.com/jobs/([A-Za-z0-9_-]+)/([A-Z0-9]{2}\.[0-9A-F]{3})")


def pages(client: httpx.Client, domain: str):
    """Yield page text from the places a careers page tends to live."""
    for path in PATHS:
        for base in (f"https://www.{domain}", f"https://{domain}"):
            try:
                response = client.get(f"{base}/{path}")
            except httpx.HTTPError:
                continue
            if response.status_code == 200 and response.text:
                yield response.text
        time.sleep(0.3)


def discover(client: httpx.Client, domain: str) -> tuple[str, str, str] | None:
    slug = domain.split(".")[0]
    uids: set[str] = set()
    tokens: set[str] = set()
    for text in pages(client, domain):
        # findall returns a tuple per alternative group; keep whichever matched.
        uids.update(g for match in UID.findall(text) for g in match if g)
        tokens.update(g for match in TOKEN.findall(text) for g in match if g)
        for hosted_slug, uid in HOSTED.findall(text):
            slug, _ = hosted_slug, uids.add(uid)
        if uids and tokens:
            break
    # A board found without its token is still worth reporting: the hosted
    # Comeet page usually carries it even when the company's own page does not.
    for uid in uids:
        for token in tokens or _tokens_from_hosted(client, slug, uid):
            if verify(client, uid, token):
                return slug, uid, token
    return None


def _tokens_from_hosted(client: httpx.Client, slug: str, uid: str) -> set[str]:
    try:
        response = client.get(f"https://www.comeet.com/jobs/{slug}/{uid}")
    except httpx.HTTPError:
        return set()
    return set(TOKEN.findall(response.text)) if response.status_code == 200 else set()


def verify(client: httpx.Client, uid: str, token: str) -> bool:
    """Only report identifiers that actually return postings."""
    try:
        response = client.get(API.format(uid=uid), params={"token": token})
    except httpx.HTTPError:
        return False
    return response.status_code == 200 and isinstance(response.json(), list)


def main(domains: list[str]) -> int:
    if not domains:
        print(__doc__)
        return 2
    client = httpx.Client(timeout=20, headers={"User-Agent": UA},
                          follow_redirects=True)
    found = 0
    for domain in domains:
        result = discover(client, domain)
        if result:
            slug, uid, token = result
            print(f'    "{slug}": ("{uid}", "{token}"),')
            found += 1
        else:
            print(f"    # {domain}: no verified Comeet board", file=sys.stderr)
        time.sleep(0.8)
    return 0 if found else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
