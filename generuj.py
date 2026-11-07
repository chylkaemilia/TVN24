import re
import html
from datetime import datetime, timezone, timedelta

import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ---------------------------------------------------------------
# CZĘŚĆ 1 - pobranie danych z TVN24
# ---------------------------------------------------------------

BASE_URL = "https://tvn24.pl/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "pl-PL,pl;q=0.9",
}

# Adres artykułu TVN24 kończy się na "-st" i numer, np. ...-kiedy-spadnie-snieg-st9326735
ARTICLE_RE = re.compile(r"-st\d+$")

r = requests.get(BASE_URL, headers=HEADERS, timeout=15)
r.raise_for_status()
r.encoding = "utf-8"
soup = BeautifulSoup(r.text, "html.parser")

list_news = []
seen = set()

for a in soup.find_all("a", href=True):
    url = urljoin(BASE_URL, a["href"]).split("?")[0].rstrip("/")
    tytul = a.get_text(" ", strip=True)

    if not ARTICLE_RE.search(url):          # pomija menu, reklamy, działy
        continue
    if url in seen or len(tytul) < 25:      # pomija duplikaty i krótkie podpisy
        continue
    seen.add(url)

    # dział, czyli pierwszy człon adresu po domenie: /tvnmeteo/..., /polska/...
    czesci = [c for c in url.replace("https://tvn24.pl/", "").split("/") if c]
    dzial = czesci[0].replace("-", " ").capitalize() if len(czesci) > 1 else ""

    list_news.append({"Wiadomosc": tytul, "Dzial": dzial, "URL": url})

df = pd.DataFrame(list_news, columns=["Wiadomosc", "Dzial", "URL"])

# Kolejność zostaje taka jak na stronie głównej (najważniejsze u góry),
# bo przy nagłówkach TVN24 nie podaje dat publikacji.

# ---------------------------------------------------------------
# CZĘŚĆ 2 - zapis strony HTML
# ---------------------------------------------------------------

MIESIACE_PL = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
               "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]

wiersze = []
for _, w in df.iterrows():
    dzial = html.escape(str(w["Dzial"])) if w["Dzial"] else ""
    wiersze.append(
        '<li class="pozycja">'
        + (f'<div class="dzial">{dzial}</div>' if dzial else "")
        + f'<a class="tytul" href="{html.escape(str(w["URL"]))}" target="_blank" rel="noopener">'
          f'{html.escape(str(w["Wiadomosc"]))}</a>'
        + '</li>'
    )

if not wiersze:
    wiersze.append('<li class="pozycja pusta">Nie udało się pobrać wiadomości. '
                   'Strona mogła zmienić układ adresów.</li>')

teraz = datetime.now(timezone(timedelta(hours=1)))
zaktualizowano = f"{teraz.day} {MIESIACE_PL[teraz.month - 1]} {teraz.year}, godz. {teraz:%H:%M}"

strona = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>TVN24 — najnowsze</title>
<style>
  :root {{
    color-scheme: light;
    --tlo: #f3f4f6;
    --karta: #ffffff;
    --tekst: #14181f;
    --przygaszony: #5b6577;
    --akcent: #d1021b;
    --linia: #e3e6ec;
    box-sizing: border-box;
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      color-scheme: dark;
      --tlo: #12151c;
      --karta: #1b1f29;
      --tekst: #edf0f5;
      --przygaszony: #9aa3b4;
      --akcent: #ff6b7f;
      --linia: #2a2f3b;
    }}
  }}
  *, *::before, *::after {{ box-sizing: inherit; }}
  body {{
    margin: 0;
    background: var(--tlo);
    color: var(--tekst);
    font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
    line-height: 1.5;
  }}
  .opakowanie {{ max-width: 46rem; margin: 0 auto; padding: 1.5rem 1rem 3rem; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 .25rem; }}
  h1 span {{ color: var(--akcent); }}
  .podpis {{ color: var(--przygaszony); font-size: .85rem; margin: 0 0 1.5rem; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  .pozycja {{
    background: var(--karta);
    border: 1px solid var(--linia);
    border-radius: .65rem;
    padding: .9rem 1rem;
    margin-bottom: .7rem;
  }}
  .dzial {{
    color: var(--akcent);
    font-size: .72rem;
    text-transform: uppercase;
    letter-spacing: .04em;
    margin-bottom: .3rem;
  }}
  .tytul {{
    color: var(--tekst);
    text-decoration: none;
    font-weight: 600;
    display: block;
  }}
  .tytul:hover, .tytul:focus {{ color: var(--akcent); text-decoration: underline; }}
  .pusta {{ color: var(--przygaszony); font-weight: 400; }}
  footer {{ margin-top: 2rem; font-size: .8rem; color: var(--przygaszony); text-align: center; }}
  footer a {{ color: var(--przygaszony); }}
</style>
</head>
<body>
  <div class="opakowanie">
    <h1>Najnowsze <span>TVN24</span></h1>
    <p class="podpis">Zaktualizowano: {zaktualizowano} &middot; pozycji: {len(df)}</p>
    <ul>
      {"".join(wiersze)}
    </ul>
    <footer>
      Tytuły i odnośniki ze strony
      <a href="https://tvn24.pl/" target="_blank" rel="noopener">tvn24.pl</a>
    </footer>
  </div>
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as plik:
    plik.write(strona)

print(f"Zapisano index.html — pozycji: {len(df)}")
