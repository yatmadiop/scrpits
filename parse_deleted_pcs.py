import requests
import pandas as pd
from bs4 import BeautifulSoup

BASE_URL = "https://www.icd10data.com/ICD10PCS/Codes/Changes/Deleted_Codes/1?year={year}"


def fetch_deleted_pcs_codes(year: int) -> pd.DataFrame:
    """
    Récupère les codes ICD-10-PCS supprimés pour une année donnée
    en parsant les <span class="identifier"> dans la page.
    Retourne un DataFrame avec colonnes : code, libelle, annee_suppression.
    """
    url = BASE_URL.format(year=year)
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; deleted-pcs-scraper/1.0)"
    }

    print(f"→ Année {year} : récupération {url}")
    resp = requests.get(url, headers=headers, timeout=15)

    if resp.status_code != 200:
        print(f"  !! Année {year} : HTTP {resp.status_code}, on saute cette année.")
        return pd.DataFrame(columns=["code", "libelle", "annee_suppression"])

    soup = BeautifulSoup(resp.text, "html.parser")

    # On se limite au contenu central de la page
    content_div = soup.find("div", class_="body-content")
    if content_div is None:
        print(f"  !! Année {year} : div.body-content introuvable, on prend tout le document.")
        content_div = soup

    rows = []

    # Tous les codes sont dans <span class="identifier">CODE</span>
    for span in content_div.find_all("span", class_="identifier"):
        code = span.get_text(strip=True)
        li = span.find_parent("li")
        if li is None:
            continue

        full_text = li.get_text(" ", strip=True)

        # On retire le code du début pour ne garder que le libellé
        if full_text.startswith(code):
            desc = full_text[len(code):].strip(" -:\u00a0")
        else:
            desc = full_text

        rows.append(
            {
                "code": code,
                "libelle": desc,
                "annee_suppression": year,
            }
        )

    df = pd.DataFrame(rows)
    print(f"  OK Année {year} : {len(df)} codes trouvés.")
    return df


def main():
    # adapte la plage d'années à ce que tu veux
    YEARS = range(2016, 2027)

    all_dfs = []

    for year in YEARS:
        df_year = fetch_deleted_pcs_codes(year)
        if df_year.empty:
            continue

        # # CSV par année
        # file_year = f"deleted_icd10pcs_{year}.csv"
        # df_year.to_csv(file_year, index=False, encoding="utf-8")
        # print(f"  Fichier annuel créé : {file_year}")

        all_dfs.append(df_year)

    if not all_dfs:
        print("Aucune donnée récupérée pour les années spécifiées.")
        return

    # CSV global toutes années confondues
    df_all = pd.concat(all_dfs, ignore_index=True)
    file_all = "deleted_icd10pcs_all_years.csv"
    df_all.to_csv(file_all, index=False, encoding="utf-8")
    print(f"\nFichier global créé : {file_all}")
    print(df_all.head())


if __name__ == "__main__":
    main()
