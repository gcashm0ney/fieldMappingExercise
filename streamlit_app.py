import streamlit as st
import pandas as pd
import io
import graphviz

st.set_page_config(layout="wide")

# Title
st.title("Data Model Relationship Builder")

# Step 1: Upload files and name them
uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if not uploaded_files:
    st.stop()

# File metadata setup
file_data = {}
st.subheader("Step 1: Name each file and select header row")

for file in uploaded_files:
    with st.expander(f"Configure: {file.name}", expanded=True):
        file_name = st.text_input(f"Name for '{file.name}'", value=file.name.split('.')[0], key=f"name_{file.name}")
        start_row = st.selectbox(f"Header starts on row:", options=range(1, 11), index=0, key=f"start_{file.name}")

        try:
            df = pd.read_csv(file, skiprows=start_row - 1, encoding='latin1', nrows=100)
        except Exception as e:
            st.error(f"Error reading file: {e}")
            continue

        file_data[file_name] = {"df": df, "start_row": start_row}
        st.dataframe(df.head())

if not file_data:
    st.warning("No files processed.")
    st.stop()

# Step 2: Define relationships
st.subheader("Step 2: Define Relationships")
st.markdown("Use the '+' button to define relationships between key fields of each file.")

if "relationships" not in st.session_state:
    st.session_state.relationships = []

# Initialize removal index BEFORE loop
if "remove_rel_idx" not in st.session_state:
    st.session_state.remove_rel_idx = None

# Add new relationship
if st.button("+ Add Relationship"):
    st.session_state.relationships.append({
        "Source File": None,
        "Source Field": None,
        "Relationship Type": "One-to-Many",
        "Target File": None,
        "Target Field": None
    })

# Loop through relationships
for idx, rel in enumerate(st.session_state.relationships):
    with st.expander(f"Relationship #{idx+1}", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            source_file = st.selectbox("Source Table", options=["-- Select Table --"] + list(file_data.keys()), key=f"src_file_{idx}")
            if source_file and source_file != "-- Select Table --":
                source_fields = sorted(file_data[source_file]["df"].columns.tolist(), key=str.lower)
            else:
                source_fields = ["-- Select Field --"]

            source_field = st.selectbox("Source Field", options=["-- Select Field --"] + source_fields, key=f"src_field_{idx}")

        with col2:
            target_file = st.selectbox("Target Table", options=["-- Select Table --"] + list(file_data.keys()), key=f"tgt_file_{idx}")
            if target_file and target_file != "-- Select Table --":
                target_fields = sorted(file_data[target_file]["df"].columns.tolist(), key=str.lower)
            else:
                target_fields = ["-- Select Field --"]

            target_field = st.selectbox("Target Field", options=["-- Select Field --"] + target_fields, key=f"tgt_field_{idx}")
            rel_type = st.selectbox("Relationship Type", ["One-to-Many", "Many-to-One", "One-to-One", "Many-to-Many"], key=f"rel_type_{idx}")

        # Save updated values
        st.session_state.relationships[idx] = {
            "Source File": source_file,
            "Source Field": source_field,
            "Relationship Type": rel_type,
            "Target File": target_file,
            "Target Field": target_field
        }

        # Add remove button
        if st.button(f"❌ Remove Relationship #{idx+1}", key=f"remove_{idx}"):
            st.session_state.remove_rel_idx = idx
            st.rerun()

# Remove selected relationship outside the loop
if st.session_state.remove_rel_idx is not None:
    del st.session_state.relationships[st.session_state.remove_rel_idx]
    st.session_state.remove_rel_idx = None
    st.rerun()


# Step 3: Validate connection coverage
st.subheader("Step 3: Connectivity Check")
connected_tables = set()
for rel in st.session_state.relationships:
    connected_tables.add(rel["Source File"])
    connected_tables.add(rel["Target File"])

all_tables = set(file_data.keys())
not_connected = all_tables - connected_tables

if not not_connected:
    st.success("All tables are connected to at least one relationship.")
else:
    st.warning(f"The following tables are not connected: {', '.join(not_connected)}")

# Step 4: Show relationships table
st.subheader("Step 4: Confirmed Relationships")
if st.session_state.relationships:
    df_rels = pd.DataFrame(st.session_state.relationships)
    st.dataframe(df_rels)

    # Download option
    output = io.StringIO()
    output.write("Confirmed Field Relationships:\n")
    for _, row in df_rels.iterrows():
        output.write(f"{row['Source File']} ({row['Source Field']}) -> {row['Target File']} ({row['Target Field']}) [{row['Relationship Type']}]\n")

    st.download_button("Download Relationship Summary", data=output.getvalue(), file_name="relationships.txt", mime="text/plain")

# Step 5: Diagram
st.subheader("Step 5: Relationship Diagram")
graph = graphviz.Digraph()

for file in file_data:
    graph.node(file)

for rel in st.session_state.relationships:
    label = f"{rel['Source Field']} ➜ {rel['Target Field']}\n({rel['Relationship Type']})"
    graph.edge(rel['Source File'], rel['Target File'], label=label)

st.graphviz_chart(graph)

# Step 6: Import and Select KPIs
kpis_df = pd.read_csv("kpis.csv")  # Load the KPI list from kpis.csv
st.header("Select KPIs for Analysis")
kpi_options = kpis_df['KPI Name'].tolist()

# Let user select KPIs
selected_kpis = st.multiselect("Select KPIs to include in the analysis", options=kpi_options)

# Track if any required field across all KPIs is unmapped
global_unmapped = False

# Step 7: Show Selected KPIs and Their Required Fields
if selected_kpis:
    selected_kpis_df = kpis_df[kpis_df['KPI Name'].isin(selected_kpis)]

    st.write("### Selected KPIs and Their Required Fields")

    for _, row in selected_kpis_df.iterrows():
        kpi_name = row['KPI Name']
        required_fields = [field.strip() for field in row['Required Fields'].split(';') if field.strip()]

        # Check if this KPI has any unmapped fields
        any_unmapped = False
        for req_field in required_fields:
            table_key = f"table_choice_{kpi_name}_{req_field}"
            field_key = f"field_choice_{kpi_name}_{req_field}"

            table_choice = st.session_state.get(table_key, "-- Select Table --")
            field_choice = st.session_state.get(field_key, "-- Select Field --")

            if table_choice == "-- Select Table --" or field_choice == "-- Select Field --":
                any_unmapped = True
                global_unmapped = True
                break

        with st.expander(f"🔹 {kpi_name}", expanded=any_unmapped):
            col1, col2 = st.columns([2, 3])

            with col1:
                st.markdown(f"**Description:** {row['KPI Description']}")
                st.markdown(f"**Formula:** `{row['KPI Formula']}`")
                st.markdown(f"**Required Fields:** {', '.join(required_fields)}")

            with col2:
                st.markdown("**Field Mapping**")
                kpi_unmapped_found = False

                for req_field in required_fields:
                    table_choice = st.selectbox(
                        f"Select table for '{req_field}'",
                        options=["-- Select Table --"] + list(file_data.keys()),
                        key=f"table_choice_{kpi_name}_{req_field}"
                    )

                    if table_choice != "-- Select Table --":
                        column_options = sorted(file_data[table_choice]["df"].columns.tolist())
                        field_choice = st.selectbox(
                            f"Select field in '{table_choice}' for '{req_field}'",
                            options=["-- Select Field --"] + column_options,
                            key=f"field_choice_{kpi_name}_{req_field}"
                        )
                        if field_choice == "-- Select Field --":
                            kpi_unmapped_found = True
                    else:
                        kpi_unmapped_found = True

                if kpi_unmapped_found:
                    st.warning("⚠️ Some required fields have not been mapped.")

# Show global warning if any field for any KPI is unmapped
if global_unmapped:
    st.warning("⚠️ Please complete all required field mappings before proceeding.")



# Step 9: Generate a Mapping Summary for KPIs
if st.button("Generate Mapping Summary for KPIs"):
    output = io.StringIO()
    output.write("Field Mappings Summary for KPIs:\n")

    for _, row in selected_kpis_df.iterrows():
        required_fields = row['Required Fields'].split(";")

        for field in required_fields:
            output.write(f"KPI: {row['KPI Name']} - Field: {field.strip()}\n")

            for file_name, data in file_data.items():
                field_mapping = st.session_state.get(f"{file_name}_{field.strip()}", "-- Select --")
                if field_mapping != "-- Select --":
                    output.write(f"  Mapped to '{field_mapping}' in '{file_name}'\n")
                else:
                    output.write(f"  Unmapped! (Calculation Required)\n")

    st.download_button(
        label="Download KPI Field Mappings Summary as TXT",
        data=output.getvalue(),
        file_name="kpi_field_mappings.txt",
        mime="text/plain"
    )