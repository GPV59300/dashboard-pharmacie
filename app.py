import streamlit as st
import pdfplumber
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="Dashboard Pharmacie PRO+", layout="wide")

st.title("🏥 Dashboard Pharmacie PRO+ (Outil de gestion complet)")

uploaded_files = st.file_uploader(
    "Importer vos synthèses mensuelles (PDF)",
    type="pdf",
    accept_multiple_files=True
)

# ---------------------- EXTRACTION ----------------------
def extract_data(pdf, filename):
    text = ""
    with pdfplumber.open(pdf) as pdf_file:
        for page in pdf_file.pages:
            text += page.extract_text()

    def extract(pattern):
        match = re.search(pattern, text)
        return float(match.group(1).replace(" ", "").replace(",", ".")) if match else None

    data = {}

    data["CA_HT"] = extract(r'Total\s+[\d\s,]+\s+100 %\s+([\d\s,]+)\s+100 %')

    clients = re.search(r'CA TTC\s+[\d\s,]+\s+EUR\s+(\d+)', text)
    data["Clients"] = int(clients.group(1)) if clients else None

    data["Panier"] = extract(r'Panier Moyen Global\s+(\d+,\d+)')

    data["Marge"] = extract(r'Totaux\s+[\d\s,]+\s+[\d\s,]+\s+(\d+,\d+)')

    # Détection date
    mois_map = {
        "janvier":1, "fevrier":2, "février":2, "mars":3,
        "avril":4, "mai":5, "juin":6,
        "juillet":7, "aout":8, "août":8,
        "septembre":9, "octobre":10,
        "novembre":11, "decembre":12, "décembre":12
    }

    filename_lower = filename.lower()

    month = next((mois_map[m] for m in mois_map if m in filename_lower), None)
    year_match = re.search(r'20\d{2}', filename_lower)
    year = int(year_match.group()) if year_match else None

    data["Date"] = datetime(year, month, 1) if month and year else None

    return data

# ---------------------- TRAITEMENT ----------------------
if uploaded_files:
    records = []

    for file in uploaded_files:
        data = extract_data(file, file.name)
        data["Fichier"] = file.name
        records.append(data)

    df = pd.DataFrame(records).dropna(subset=["Date"]).sort_values("Date")

    st.subheader("📋 Historique")
    st.dataframe(df)

    # ---------------- KPI ----------------
    st.subheader("📊 Indicateurs clés")

    latest = df.iloc[-1]

    def get_n1(row):
        return df[(df["Date"].dt.month == row["Date"].month) &
                  (df["Date"].dt.year == row["Date"].year - 1)]

    n1_df = get_n1(latest)
    n1 = n1_df.iloc[0] if not n1_df.empty else None

    def variation(a, b):
        return ((a - b) / b * 100) if b else None

    col1, col2, col3, col4 = st.columns(4)

    if n1 is not None:
        col1.metric("CA HT", f"{latest['CA_HT']:.0f} €", f"{variation(latest['CA_HT'], n1['CA_HT']):.1f}%")
        col2.metric("Clients", f"{int(latest['Clients'])}", f"{variation(latest['Clients'], n1['Clients']):.1f}%")
        col3.metric("Panier", f"{latest['Panier']:.2f} €", f"{variation(latest['Panier'], n1['Panier']):.1f}%")
        col4.metric("Marge", f"{latest['Marge']:.2f} %", f"{variation(latest['Marge'], n1['Marge']):.1f}%")
    else:
        st.warning("Pas de comparaison N-1 disponible")

    # ---------------- ALERTES ----------------
    st.subheader("🚨 Alertes")

    alerts = []

    if n1 is not None:
        if latest["CA_HT"] < n1["CA_HT"]:
            alerts.append("⚠️ Baisse du CA")
        if latest["Panier"] < n1["Panier"]:
            alerts.append("⚠️ Baisse du panier moyen")
        if latest["Marge"] < n1["Marge"]:
            alerts.append("⚠️ Baisse de la marge")

    if alerts:
        for a in alerts:
            st.error(a)
    else:
        st.success("RAS 👍")

    # ---------------- ANALYSE AUTO ----------------
    st.subheader("🧠 Analyse automatique")

    if n1 is not None:
        delta_clients = variation(latest['Clients'], n1['Clients'])
        delta_panier = variation(latest['Panier'], n1['Panier'])

        if delta_clients > delta_panier:
            st.write("La croissance est principalement tirée par le trafic client.")
        else:
            st.write("La croissance est principalement tirée par le panier moyen.")

    # ---------------- GRAPHIQUES ----------------
    st.subheader("📈 Évolution")

    df_graph = df.set_index("Date")

    st.line_chart(df_graph[["CA_HT"]])
    st.line_chart(df_graph[["Clients"]])
    st.line_chart(df_graph[["Panier"]])
    st.line_chart(df_graph[["Marge"]])

    # ---------------- EXPORT ----------------
    st.subheader("📥 Export")

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Télécharger CSV", csv, "dashboard.csv", "text/csv")

    # ---------------- SAUVEGARDE LOCALE ----------------
    st.subheader("💾 Sauvegarde")

    if st.button("Sauvegarder les données localement"):
        df.to_csv("historique_pharmacie.csv", index=False)
        st.success("Données sauvegardées")

else:
    st.info("⬆️ Charge tes fichiers PDF pour démarrer")
