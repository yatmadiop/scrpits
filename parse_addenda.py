import os
import re
import pandas as pd

# ---------------------------
# 1. Parsing des fichiers ORDER
# ---------------------------

# Regex pour les lignes de icd10pcs_order_YYYY.txt
# Exemple de ligne :
# 00002 0016070 1 Bypass Cereb Vent ...  Bypass Cerebral Ventricle ...
ORDER_PATTERN = re.compile(
    r"""^\s*\d+\s+        # index numérique
        (?P<code>[A-Z0-9]{7})\s+  # code à 7 caractères
        \d\s+             # niveau (0/1/...)
        (?P<short>.+?)    # libellé abrégé
        (?:\s{2,}(?P<long>.+))?  # libellé long optionnel
        \s*$""",
    re.VERBOSE,
)

def parse_order_file(path: str, year: int) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = ORDER_PATTERN.match(line)
            if not m:
                continue
            code = m.group("code").strip()
            short = (m.group("short") or "").strip()
            long = (m.group("long") or "").strip()

            # On choisit le libellé long si présent, sinon le court
            label = long if long else short

            rows.append(
                {
                    "year_order": year,
                    "code": code,
                    "libelle": label,
                    "libelle_court": short,
                    "libelle_long": long,
                }
            )
    return pd.DataFrame(rows)


def build_order_df(base_dir: str, year_start: int, year_end: int) -> pd.DataFrame:
    all_rows = []
    for year in range(year_start, year_end + 1):
        filename = f"icd10pcs_order_{year}.txt"
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"[ORDER] Fichier manquant : {path} (ignoré)")
            continue
        print(f"[ORDER] Parsing {path}")
        df_year = parse_order_file(path, year)
        print(f"  -> {len(df_year)} codes trouvés pour {year}")
        all_rows.append(df_year)

    if not all_rows:
        return pd.DataFrame(columns=["code", "libelle"])

    df_all = pd.concat(all_rows, ignore_index=True)

    # On déduplique par code : on garde le libellé de la dernière année
    df_all_sorted = df_all.sort_values(["code", "year_order"])
    df_unique = df_all_sorted.drop_duplicates(subset=["code"], keep="last")

    return df_unique[["code", "libelle"]]


# ---------------------------
# 2. Parsing des fichiers ADDENDA (Delete)
# ---------------------------

# Exemple de ligne :
# "     Delete            Intravascular Optical Coherence B52TZ2Z"
DELETE_PATTERN = re.compile(
    r"\bDelete\b(?P<desc>.*?)(?P<code>[A-Z0-9]{7})\s*$"
)

def parse_addenda_file(path: str, year: int) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Delete" not in line:
                continue
            m = DELETE_PATTERN.search(line)
            if not m:
                continue
            code = m.group("code").strip()
            desc = m.group("desc").strip()
            rows.append(
                {
                    "annee_suppression": year,
                    "code": code,
                    "desc_addenda": desc,
                }
            )
    return pd.DataFrame(rows)


def build_deleted_df(base_dir: str, year_start: int, year_end: int) -> pd.DataFrame:
    all_rows = []
    for year in range(year_start, year_end + 1):
        filename = f"index_addenda_{year}.txt"
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"[ADDENDA] Fichier manquant : {path} (ignoré)")
            continue
        print(f"[ADDENDA] Parsing {path}")
        df_year = parse_addenda_file(path, year)
        print(f"  -> {len(df_year)} codes 'Delete' trouvés pour {year}")
        all_rows.append(df_year)

    if not all_rows:
        return pd.DataFrame(columns=["annee_suppression", "code", "desc_addenda"])

    return pd.concat(all_rows, ignore_index=True)


# ---------------------------
# 3. Construction du DF global et croisement
# ---------------------------

def main():
    base_dir = "source"          # adapte si tes fichiers sont dans un autre dossier
    year_start = 2014
    year_end = 2026

    # 1) DF contenant tous les codes + libellés (ORDER)
    df_order_all = build_order_df(base_dir, year_start, year_end)
    print(f"\n[ORDER] Total codes distincts : {len(df_order_all)}")

    # 2) DF contenant tous les codes Delete (ADDENDA)
    df_deleted = build_deleted_df(base_dir, year_start, year_end)
    print(f"[ADDENDA] Total codes 'Delete' : {len(df_deleted)}")

    # 3) Croisement : on récupère les libellés à partir de df_order_all
    df_deleted_with_labels = df_deleted.merge(
        df_order_all, on="code", how="left"
    )
    
    df_deleted_with_labels = df_deleted_with_labels[["code", "libelle", "annee_suppression"]]


    # Sauvegardes
    df_order_all.to_csv("icd10pcs_all_codes_labels.csv", index=False, encoding="utf-8")
    df_deleted_with_labels.to_csv(
        "icd10pcs_deleted_with_labels.csv", index=False, encoding="utf-8"
    )

    print("\nFichiers générés :")
    print("  - icd10pcs_all_codes_labels.csv  (tous les codes + libellés)")
    print("  - icd10pcs_deleted_with_labels.csv  (codes supprimés + année + libellé)")


if __name__ == "__main__":
    main()
import os
import re
import pandas as pd

# ---------------------------
# 1. Parsing des fichiers ORDER
# ---------------------------

# Regex pour les lignes de icd10pcs_order_YYYY.txt
# Exemple de ligne :
# 00002 0016070 1 Bypass Cereb Vent ...  Bypass Cerebral Ventricle ...
ORDER_PATTERN = re.compile(
    r"""^\s*\d+\s+        # index numérique
        (?P<code>[A-Z0-9]{7})\s+  # code à 7 caractères
        \d\s+             # niveau (0/1/...)
        (?P<short>.+?)    # libellé abrégé
        (?:\s{2,}(?P<long>.+))?  # libellé long optionnel
        \s*$""",
    re.VERBOSE,
)

def parse_order_file(path: str, year: int) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = ORDER_PATTERN.match(line)
            if not m:
                continue
            code = m.group("code").strip()
            short = (m.group("short") or "").strip()
            long = (m.group("long") or "").strip()

            # On choisit le libellé long si présent, sinon le court
            label = long if long else short

            rows.append(
                {
                    "year_order": year,
                    "code": code,
                    "libelle": label,
                    "libelle_court": short,
                    "libelle_long": long,
                }
            )
    return pd.DataFrame(rows)


def build_order_df(base_dir: str, year_start: int, year_end: int) -> pd.DataFrame:
    all_rows = []
    for year in range(year_start, year_end + 1):
        filename = f"icd10pcs_order_{year}.txt"
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"[ORDER] Fichier manquant : {path} (ignoré)")
            continue
        print(f"[ORDER] Parsing {path}")
        df_year = parse_order_file(path, year)
        print(f"  -> {len(df_year)} codes trouvés pour {year}")
        all_rows.append(df_year)

    if not all_rows:
        return pd.DataFrame(columns=["code", "libelle"])

    df_all = pd.concat(all_rows, ignore_index=True)

    # On déduplique par code : on garde le libellé de la dernière année
    df_all_sorted = df_all.sort_values(["code", "year_order"])
    df_unique = df_all_sorted.drop_duplicates(subset=["code"], keep="last")

    return df_unique[["code", "libelle"]]


# ---------------------------
# 2. Parsing des fichiers ADDENDA (Delete)
# ---------------------------

# Exemple de ligne :
# "     Delete            Intravascular Optical Coherence B52TZ2Z"
DELETE_PATTERN = re.compile(
    r"\bDelete\b(?P<desc>.*?)(?P<code>[A-Z0-9]{7})\s*$"
)

def parse_addenda_file(path: str, year: int) -> pd.DataFrame:
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "Delete" not in line:
                continue
            m = DELETE_PATTERN.search(line)
            if not m:
                continue
            code = m.group("code").strip()
            desc = m.group("desc").strip()
            rows.append(
                {
                    "annee_suppression": year,
                    "code": code,
                    "desc_addenda": desc,
                }
            )
    return pd.DataFrame(rows)


def build_deleted_df(base_dir: str, year_start: int, year_end: int) -> pd.DataFrame:
    all_rows = []
    for year in range(year_start, year_end + 1):
        filename = f"index_addenda_{year}.txt"
        path = os.path.join(base_dir, filename)
        if not os.path.exists(path):
            print(f"[ADDENDA] Fichier manquant : {path} (ignoré)")
            continue
        print(f"[ADDENDA] Parsing {path}")
        df_year = parse_addenda_file(path, year)
        print(f"  -> {len(df_year)} codes 'Delete' trouvés pour {year}")
        all_rows.append(df_year)

    if not all_rows:
        return pd.DataFrame(columns=["annee_suppression", "code", "desc_addenda"])

    return pd.concat(all_rows, ignore_index=True)


# ---------------------------
# 3. Construction du DF global et croisement
# ---------------------------

def main():
    base_dir = "source"          # adapte si tes fichiers sont dans un autre dossier
    year_start = 2014
    year_end = 2026

    # 1) DF contenant tous les codes + libellés (ORDER)
    df_order_all = build_order_df(base_dir, year_start, year_end)
    print(f"\n[ORDER] Total codes distincts : {len(df_order_all)}")

    # 2) DF contenant tous les codes Delete (ADDENDA)
    df_deleted = build_deleted_df(base_dir, year_start, year_end)
    print(f"[ADDENDA] Total codes 'Delete' : {len(df_deleted)}")

    # 3) Croisement : on récupère les libellés à partir de df_order_all
    df_deleted_with_labels = df_deleted.merge(
        df_order_all, on="code", how="left"
    )
    
    df_deleted_with_labels = df_deleted_with_labels[["code", "libelle", "annee_suppression"]]


    # Sauvegardes
    df_order_all.to_csv("icd10pcs_all_codes_labels.csv", index=False, encoding="utf-8")
    df_deleted_with_labels.to_csv(
        "icd10pcs_deleted_with_labels.csv", index=False, encoding="utf-8"
    )

    print("\nFichiers générés :")
    print("  - icd10pcs_all_codes_labels.csv  (tous les codes + libellés)")
    print("  - icd10pcs_deleted_with_labels.csv  (codes supprimés + année + libellé)")


if __name__ == "__main__":
    main()
