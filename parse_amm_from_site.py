import io
import requests
import pandas as pd
import certifi

URL = "https://arp.sn/liste-des-amms/"
CSV_OUTPUT = "liste_des_amms.csv"

def main():
    print(f"Téléchargement de {URL} ...")
    resp = requests.get(URL, verify=certifi.where(), timeout=30)
    resp.raise_for_status()

    text = resp.text
    content_type = resp.headers.get("Content-Type", "").lower()

    if "html" in content_type:
        print("→ Contenu HTML, tentative de lecture de tableaux.")
        tables = pd.read_html(text)
        if not tables:
            raise ValueError("Aucun tableau HTML trouvé sur la page.")
        df = tables[0]
    else:
        # fallback très simple : essayer de lire comme CSV avec ;
        df = pd.read_csv(io.StringIO(text), sep=";", engine="python")

    df = df.dropna(how="all", axis=1)
    print(df.head())
    df.to_csv(CSV_OUTPUT, index=False, encoding="utf-8-sig")
    print(f"✅ Fichier sauvegardé : {CSV_OUTPUT}")

if __name__ == "__main__":
    main()
