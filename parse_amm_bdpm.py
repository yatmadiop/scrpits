import warnings
import unicodedata
from difflib import get_close_matches

import pandas as pd
import requests
import urllib3


# =========================
# PARAMÈTRES
# =========================

URL_ARP = "https://arp.sn/liste-des-amms/"
FICHIER_COMPO = "CIS_COMPO_bdpm.txt"               # chemin vers COMPO

FICHIER_SUBSTANCES = "substances_par_medicament.csv"
FICHIER_MEDICAMENTS = "codes_medicaments.csv"
FICHIER_SUBSTANCES_NON_TROUVEES = "substances_non_trouvees_detail.csv"
FICHIER_SUBSTANCES_NON_TROUVEES_UNIQUES = "substances_non_trouvees_unique.csv"

NB_CHIFFRES_CODE = 6  # ARP000001, ARP000002, ...


# =========================
# FONCTIONS UTILITAIRES
# =========================

def normalise_chaine(s: str) -> str:
    if pd.isna(s):
        return ""
    s = str(s)
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.upper()
    s = s.replace("'", " ")
    s = s.replace("-", " ")
    s = " ".join(s.split())
    return s


def find_col_by_pattern(df, patterns):
    cols = df.columns.astype(str)
    cols_lower = [c.lower() for c in cols]
    for pat in patterns:
        for col, col_l in zip(cols, cols_lower):
            if pat in col_l:
                return col
    raise KeyError(f"Aucune colonne ne correspond aux patterns : {patterns}")


def main():
    # Désactiver les warnings SSL (verify=False à cause du certificat ARP)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # 1) Télécharger & parser la page ARP
    print(f"Téléchargement de {URL_ARP} ...")
    resp = requests.get(URL_ARP, verify=False, timeout=60)
    resp.raise_for_status()
    html = resp.text

    print("Lecture des tableaux HTML ...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tables = pd.read_html(html)

    if not tables:
        raise ValueError("Aucun tableau HTML trouvé sur la page ARP.")

    # On prend le tableau qui a un nom + une DCI
    df_arp = None
    for t in tables:
        cols = [c.lower() for c in t.columns.astype(str)]
        if any("nom" in c for c in cols) and any("dci" in c for c in cols):
            df_arp = t
            break
    if df_arp is None:
        df_arp = tables[0]

    print("Colonnes ARP :")
    print(df_arp.columns)

    # Colonnes importantes
    try:
        col_nom = find_col_by_pattern(df_arp, ["nom du medicament", "nom du médicament", "nom"])
    except KeyError:
        col_nom = "Nom du Medicament"

    try:
        col_dci = find_col_by_pattern(df_arp, ["dci"])
    except KeyError:
        col_dci = "DCI"

    print(f"Colonne Nom du Medicament = {col_nom}")
    print(f"Colonne DCI = {col_dci}")

    # 2) Code ARP par médicament
    noms_uniques = (
        df_arp[col_nom]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    mapping_arp = {
        nom: f"ARP{idx:0{NB_CHIFFRES_CODE}d}"
        for idx, nom in enumerate(noms_uniques, start=1)
    }

    df_arp["Code_ARP"] = df_arp[col_nom].map(mapping_arp)

    # Libellé médicament = Nom + " - " + Conditionnement
    if "Conditionnement" in df_arp.columns:
        df_arp["Libelle_medicament"] = (
            df_arp[col_nom].astype(str).str.strip()
            + " - "
            + df_arp["Conditionnement"].astype(str).str.strip()
        )
    else:
        df_arp["Libelle_medicament"] = df_arp[col_nom].astype(str).str.strip()

    # 3) Découper la DCI en substances (séparées par "/")
    df_arp["DCI_brute"] = df_arp[col_dci].astype(str)

    df_arp_sub = (
        df_arp
        .assign(
            Substance_texte=lambda d: d["DCI_brute"].str.split("/")
        )
        .explode("Substance_texte")
    )

    df_arp_sub["Substance_texte"] = (
        df_arp_sub["Substance_texte"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    df_arp_sub = df_arp_sub[df_arp_sub["Substance_texte"] != ""].copy()
    df_arp_sub["Substance_norm"] = df_arp_sub["Substance_texte"].map(normalise_chaine)

    # 4) Charger COMPO et préparer le mapping substances
    print(f"Lecture COMPO : {FICHIER_COMPO}")
    cols_compo = [
        "Code_CIS",
        "Designation_element",
        "Code_substance",
        "Libelle_substance",
        "Dosage_substance",
        "Reference_dosage",
        "Nature_composant",
        "Num_liaison",
    ]

    df_compo = pd.read_csv(
        FICHIER_COMPO,
        sep="\t",
        header=None,
        names=cols_compo,
        encoding="latin-1",
    )

    # On garde tout (SA, FT, etc.) pour ne pas perdre AMOXICILLINE & co
    df_compo["Libelle_norm"] = df_compo["Libelle_substance"].map(normalise_chaine)

    df_substances = (
        df_compo
        .sort_values("Code_substance")
        .drop_duplicates(subset=["Libelle_norm"])
        .loc[:, ["Libelle_norm", "Code_substance", "Libelle_substance"]]
        .reset_index(drop=True)
    )

    dict_exact = {
        row["Libelle_norm"]: (row["Code_substance"], row["Libelle_substance"])
        for _, row in df_substances.iterrows()
    }
    all_norm_names = list(dict_exact.keys())

    def match_substance(norm_name: str, cutoff: float = 0.8):
        # 1) exact
        if norm_name in dict_exact:
            return dict_exact[norm_name]
        # 2) flou
        matches = get_close_matches(norm_name, all_norm_names, n=1, cutoff=cutoff)
        if matches:
            best = matches[0]
            return dict_exact[best]
        return (None, None)

    codes = []
    labels = []
    for norm_name in df_arp_sub["Substance_norm"]:
        code_sub, lib_sub = match_substance(norm_name)
        codes.append(code_sub)
        labels.append(lib_sub)

    df_arp_sub["Code_substance"] = codes
    df_arp_sub["Libelle_substance"] = labels

    # =========================
    # 5) FICHIER 1 : SUBSTANCE / MEDICAMENT (match trouvés)
    # =========================
    df_sub_out = (
        df_arp_sub[["Code_substance", "Libelle_substance", "Code_ARP"]]
        .dropna(subset=["Code_substance"])      # on enlève les non matchés
        .drop_duplicates()
        .reset_index(drop=True)
    )

    df_sub_out.to_csv(FICHIER_SUBSTANCES, index=False, sep=";", encoding="utf-8-sig")
    print(f"✅ Fichier substances créé : {FICHIER_SUBSTANCES}")

    # =========================
    # 6) FICHIER 2 : MEDICAMENTS (Code_ARP + libellé complet)
    # =========================
    df_med_out = (
        df_arp[["Code_ARP", "Libelle_medicament"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    df_med_out.to_csv(FICHIER_MEDICAMENTS, index=False, sep=";", encoding="utf-8-sig")
    print(f"✅ Fichier médicaments créé : {FICHIER_MEDICAMENTS}")

    # =========================
    # 7) FICHIERS NON TROUVÉS
    # =========================

    # a) Détail : chaque substance non matchée avec son contexte
    df_unmatched = df_arp_sub[df_arp_sub["Code_substance"].isna()].copy()

    cols_detail = [
        "Code_ARP",
        "Libelle_medicament",
        "DCI_brute",
        "Substance_texte",
        "Substance_norm",
    ]
    cols_detail = [c for c in cols_detail if c in df_unmatched.columns]

    df_unmatched_detail = (
        df_unmatched[cols_detail]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    df_unmatched_detail.to_csv(
        FICHIER_SUBSTANCES_NON_TROUVEES,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )
    print(f"✅ Fichier non trouvés (détail) : {FICHIER_SUBSTANCES_NON_TROUVEES}")

    # b) Vue unique : chaque Substance_norm non matchée + compteur
    df_unmatched_unique = (
        df_unmatched_detail
        .groupby(["Substance_norm", "Substance_texte"], as_index=False)
        .agg(Nb_medicaments=("Code_ARP", "nunique"))
        .sort_values("Nb_medicaments", ascending=False)
        .reset_index(drop=True)
    )

    df_unmatched_unique.to_csv(
        FICHIER_SUBSTANCES_NON_TROUVEES_UNIQUES,
        index=False,
        sep=";",
        encoding="utf-8-sig",
    )
    print(f"✅ Fichier non trouvés (unique) : {FICHIER_SUBSTANCES_NON_TROUVEES_UNIQUES}")

    # petit aperçu
    print("\nAperçu substances matchées :")
    print(df_sub_out.head())
    print("\nAperçu substances non trouvées (unique) :")
    print(df_unmatched_unique.head())


if __name__ == "__main__":
    main()
