
import pandas as pd
from pathlib import Path
from langdetect import detect_langs
from deep_translator import GoogleTranslator
import re
import time

# ------------------------
#  Détection & traduction
# ------------------------

def _detect_language(text: str) -> tuple[str, float]:
    """Retourne (code_langue, confiance). 'und' si indéterminée."""
    if not text or not str(text).strip() or not detect_langs:
        return "und", 0.0
    try:
        cand = detect_langs(str(text))[0]           # p.ex. [en:0.99]
        code = cand.lang.split("-")[0].lower()      # normalise
        return code, float(cand.prob)
    except Exception:
        return "und", 0.0


def _translate(text: str, target: str = "fr") -> str:
    """Traduit via GoogleTranslator (deep-translator)."""
    if not GoogleTranslator:
        return text
    if not str(text).strip():
        return ""
    try:
        return GoogleTranslator(source="auto", target=target).translate(str(text))
    except Exception:
        # En cas d’échec, on renvoie le texte d’origine pour ne pas polluer l’Excel
        return text


# ------------------------
#  Pipeline Excel -> Excel
# ------------------------

def translate_excel_to_french(
    input_xlsx: str,
    output_xlsx: str,
    target_lang: str = "fr",
    batch_size: int = 200,
    min_conf: float = 0.60,
):
    """
    - Charge le Excel d'entrée
    - Traduit en français tous les champs texte par batch
    - Sauvegarde le résultat dans output_xlsx
    """

    input_xlsx = Path(input_xlsx)
    output_xlsx = Path(output_xlsx)

    print(f"Lecture: {input_xlsx}")
    df = pd.read_excel(input_xlsx)

    # Colonnes à traiter : toutes les colonnes texte (object)
    text_cols = [c for c in df.columns if df[c].dtype == "object"]
    print(f"Colonnes texte traitées: {text_cols}")

    # Cache pour éviter de traduire plusieurs fois la même chaîne
    cache: dict[str, str] = {}

    n_rows = len(df)
    print(f"{n_rows} lignes à traiter…")

    for start in range(0, n_rows, batch_size):
        end = min(start + batch_size, n_rows)
        print(f"Batch {start} → {end-1}")

        # Boucle sur les lignes du batch
        for idx in range(start, end):
            for col in text_cols:
                val = df.at[idx, col]

                if not isinstance(val, str):
                    continue

                txt = val.strip()
                if not txt:
                    continue

                # Utiliser la traduction déjà faite si possible
                if txt in cache:
                    df.at[idx, col] = cache[txt]
                    continue

                # Détection de langue
                lang, conf = _detect_language(txt)

                # Si déjà en français ou confiance faible => on ne touche pas
                if lang in ("fr", "und") or conf < min_conf:
                    translated = txt
                else:
                    translated = _translate(txt, target_lang)

                cache[txt] = translated
                df.at[idx, col] = translated

        # Petite pause pour être gentil avec l'API Google (optionnel)
        time.sleep(0.5)

    # Sauvegarde finale
    df.to_excel(output_xlsx, index=False)
    print(f"Fichier traduit sauvegardé dans: {output_xlsx}")


if __name__ == "__main__":
    translate_excel_to_french(
        input_xlsx="source/sitetype.icdo3.d20220429 (1).xlsx",
        output_xlsx="files/sitetype.icdo3.d20220429.fr.xlsx",
        target_lang="fr",
        batch_size=200,
    )
