import streamlit as st
import pandas as pd


st.title("Field Mapping Exercise")

# 1. Upload main data file
uploaded_data_file = st.file_uploader("Upload client data file (CSV)", type="csv")

# 2. Load KPI definition CSV automatically
# Assumes you have a 'kpis.csv' in the same directory
@st.cache_data
def load_kpi_definitions():
    return pd.read_csv("kpis.csv")

kpi_df = load_kpi_definitions()

# 3. Show list of KPIs with checkboxes
st.header("Select KPIs to include:")
selected_kpis = []

for kpi in kpi_df["KPI Name"].unique():
    if st.checkbox(kpi):
        selected_kpis.append(kpi)

# 4. Get required fields from selected KPIs
if selected_kpis:
    st.subheader("Step 2: Map Required Fields")
    required_fields = kpi_df[kpi_df["KPI Name"].isin(selected_kpis)]["Required Field"].unique()

    # Read uploaded client data
    if uploaded_data_file:
        uploaded_data_file.seek(0)
        client_df = pd.read_csv(uploaded_data_file, skiprows=6)  # adjust if needed
        client_columns = client_df.columns.tolist()

        # Collect mappings
        mapping = {}
        for field in required_fields:
            mapping[field] = st.selectbox(
                f"Map required field '{field}' to client field:",
                options=["-- Select --"] + client_columns,
                key=field
            )

        # 5. Output mappings
        if st.button("Generate Field Mapping Output"):
            output_text = "Field Mapping Summary:\n\n"
            for k, v in mapping.items():
                if v and v != "-- Select --":
                    output_text += f'"{k}" → "{v}"\n'
                else:
                    output_text += f'"{k}" → [NOT MAPPED]\n'

            # Display and offer download
            st.text_area("Preview of Field Mappings", output_text, height=200)

            # Downloadable text file
            st.download_button("Download Mapping as .txt", data=output_text, file_name="field_mapping.txt")
else:
    st.info("Select at least one KPI to begin field mapping.")