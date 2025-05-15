import streamlit as st
import pandas as pd
import graphviz
import os
import io
import re
import hashlib


# Constants
REQUIRED_KPI_COLUMNS = {"KPI Name", "KPI Description", "KPI Formula", "Required Fields"}

# Global state containers
file_data = {}
relationships = []
table_purposes = {}

# Helper Functions

def get_sorted_fields(table_name):
    return sorted(file_data[table_name]["df"].columns.tolist(), key=str.lower)

def display_progress(current_step, total_steps):
    st.progress(current_step / total_steps)
    steps = [
        "Upload Files",
        "Classify Table Purposes",
        "Define Relationships",
        "Visualize Relationships",
        "Load KPI File"
    ]
    for step_num, step_label in enumerate(steps, start=1):
        if step_num < current_step:
            st.markdown(f"✅ Step {step_num}: {step_label}")
        elif step_num == current_step:
            st.markdown(f"🔵 Step {step_num}: {step_label}")
        else:
            st.markdown(f"⚪ Step {step_num}: {step_label}")

# Step 1: Upload files
def upload_files():
    st.header("Step 1: Upload CSV Files")
    uploaded_files = st.file_uploader("Upload one or more CSV files", type="csv", accept_multiple_files=True, key="main_file_uploader")

    # Clear file_data and flag on new uploads
    if uploaded_files and not st.session_state.get("files_uploaded_once"):
        file_data.clear()
        st.session_state.files_uploaded_once = True

    if uploaded_files:
        for i, file in enumerate(uploaded_files):
            file_label = f"{file.name}_{i}"
            with st.expander(f"Configure: {file.name}", expanded=True):
                file_name = st.text_input(f"Name for '{file.name}'", value=file.name.split('.')[0], key=f"name_{file_label}")
                start_row = st.selectbox(f"Header starts on row:", options=range(1, 11), index=0, key=f"start_{file_label}")
            try:
                df = pd.read_csv(file, skiprows=start_row - 1, encoding='latin1', nrows=100)
                st.session_state.file_data[file_name] = {"df": df, "start_row": start_row}
                st.dataframe(df.head())
                st.success(f"Uploaded and parsed: {file.name}")
            except Exception as e:
                st.error(f"Error reading {file.name}: {e}")
    return uploaded_files

# Step 2: Classify table purposes
def define_table_purposes():
    st.header("Step 2: Classify Table Purposes")

    import hashlib
    import re

    for i, table_name in enumerate(st.session_state.file_data.keys()):
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
        name_hash = hashlib.md5(table_name.encode()).hexdigest()[:6]
        unique_key = f"purpose_{safe_name}_{i}_{name_hash}"

        purpose = st.selectbox(
            f"Select purpose for '{table_name}':",
            ["Fact", "Dimension", "Lookup"],
            key=unique_key
        )
        st.session_state.table_purposes[table_name] = purpose

def define_relationships():
    st.subheader("Step 2: Define Relationships")
    st.markdown("Use the '+' button to define relationships between key fields of each file.")

    if "relationships" not in st.session_state:
        st.session_state.relationships = []

    if "remove_rel_idx" not in st.session_state:
        st.session_state.remove_rel_idx = None

    if st.button("+ Add Relationship"):
        st.session_state.relationships.append({
            "Source File": None,
            "Source Field": None,
            "Relationship Type": "One-to-Many",
            "Target File": None,
            "Target Field": None
        })

    for idx, rel in enumerate(st.session_state.relationships):
        with st.expander(f"Relationship #{idx+1}", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                source_file = st.selectbox(
                    "Source Table",
                    options=["-- Select Table --"] + list(file_data.keys()),
                    key=f"src_file_{idx}"
                )
                if source_file and source_file != "-- Select Table --":
                    source_fields = sorted(file_data[source_file]["df"].columns.tolist(), key=str.lower)
                else:
                    source_fields = ["-- Select Field --"]
                source_field = st.selectbox("Source Field", options=["-- Select Field --"] + source_fields, key=f"src_field_{idx}")

            with col2:
                target_file = st.selectbox(
                    "Target Table",
                    options=["-- Select Table --"] + list(file_data.keys()),
                    key=f"tgt_file_{idx}"
                )
                if target_file and target_file != "-- Select Table --":
                    target_fields = sorted(file_data[target_file]["df"].columns.tolist(), key=str.lower)
                else:
                    target_fields = ["-- Select Field --"]
                target_field = st.selectbox("Target Field", options=["-- Select Field --"] + target_fields, key=f"tgt_field_{idx}")

                rel_type = st.selectbox(
                    "Relationship Type",
                    ["One-to-Many", "Many-to-One", "One-to-One", "Many-to-Many"],
                    key=f"rel_type_{idx}"
                )

            # Save updated values
            st.session_state.relationships[idx] = {
                "Source File": source_file,
                "Source Field": source_field,
                "Relationship Type": rel_type,
                "Target File": target_file,
                "Target Field": target_field
            }

            if st.button(f"❌ Remove Relationship #{idx+1}", key=f"remove_{idx}"):
                st.session_state.remove_rel_idx = idx
                st.rerun()

    if st.session_state.remove_rel_idx is not None:
        del st.session_state.relationships[st.session_state.remove_rel_idx]
        st.session_state.remove_rel_idx = None
        st.rerun()

def connectivity_check():
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

def show_relationship_summary():
    st.subheader("Step 4: Confirmed Relationships")
    if st.session_state.relationships:
        df_rels = pd.DataFrame(st.session_state.relationships)
        st.dataframe(df_rels)

        output = io.StringIO()
        output.write("Confirmed Field Relationships:\n")
        for _, row in df_rels.iterrows():
            output.write(f"{row['Source File']} ({row['Source Field']}) -> "
                         f"{row['Target File']} ({row['Target Field']}) [{row['Relationship Type']}]\n")

        st.download_button("Download Relationship Summary",
                           data=output.getvalue(),
                           file_name="relationships.txt",
                           mime="text/plain")

def show_relationship_diagram():
    st.subheader("Step 5: Relationship Diagram")
    graph = graphviz.Digraph()

    for file in file_data:
        graph.node(file)

    for rel in st.session_state.relationships:
        label = f"{rel['Source Field']} ➜ {rel['Target Field']}\n({rel['Relationship Type']})"
        graph.edge(rel['Source File'], rel['Target File'], label=label)

    st.graphviz_chart(graph)


def load_kpi_csv():
    st.header("Step 5: Load KPI File")

    option = st.radio(
        "Choose a KPI source:",
        ["Use built-in kpis.csv", "Upload my own file"],
        key="kpi_option"
    )

    kpis_df = None

    if option == "Use built-in kpis.csv":
        built_in_path = "kpis.csv"
        if os.path.exists(built_in_path):
            try:
                kpis_df = pd.read_csv(built_in_path)
                st.success("Loaded built-in KPI file.")
            except Exception as e:
                st.error(f"Error reading built-in KPI file: {e}")
        else:
            st.error("Built-in kpis.csv file not found in the working directory.")

    elif option == "Upload my own file":
        # Show instructions only when uploading own file
        with st.expander("Instructions: KPI File Structure", expanded=True):
            st.markdown("""
            Your KPI CSV file should have the following columns:

            - **KPI Name**: Unique name for each KPI.
            - **KPI Description**: A short description explaining the KPI.
            - **KPI Formula**: The formula or logic used to calculate the KPI.
            - **Required Fields**: Semicolon-separated list of fields required for the KPI (e.g., `Sales Amount; Date; Product ID`).

            Make sure all required columns are present, and fields are spelled correctly.
            """)

        uploaded_kpi_file = st.file_uploader("Upload your KPI file", type="csv", key="kpi_upload")
        if uploaded_kpi_file:
            try:
                kpis_df = pd.read_csv(uploaded_kpi_file)
                st.success("Uploaded KPI file successfully.")
            except Exception as e:
                st.error(f"Error reading uploaded KPI file: {e}")

    # Validate and preview KPI file
    if kpis_df is not None:
        st.subheader("KPI Preview")
        st.dataframe(kpis_df.head())

        missing_columns = REQUIRED_KPI_COLUMNS - set(kpis_df.columns)
        if missing_columns:
            st.error(f"Missing required KPI columns: {', '.join(missing_columns)}")
            return None
        else:
            st.success("KPI file is valid and complete.")
            return kpis_df

    return None


def kpi_selection_and_mapping(kpis_df, file_data):
    st.header("Step 6: Select KPIs for Analysis")

    kpi_options = kpis_df['KPI Name'].tolist()
    selected_kpis = st.multiselect("Select KPIs to include in the analysis", options=kpi_options)

    global_unmapped = False

    if selected_kpis:
        selected_kpis_df = kpis_df[kpis_df['KPI Name'].isin(selected_kpis)]

        for _, row in selected_kpis_df.iterrows():
            kpi_name = row['KPI Name']
            required_fields = [field.strip() for field in row['Required Fields'].split(';') if field.strip()]

            # Flag if any required field mapping is missing
            any_unmapped = False

            with st.expander(f"🔹 {kpi_name}", expanded=True):
                col1, col2 = st.columns([2, 3])

                with col1:
                    st.markdown(f"**Description:** {row['KPI Description']}")
                    st.markdown(f"**Formula:** `{row['KPI Formula']}`")
                    st.markdown(f"**Required Fields:** {', '.join(required_fields)}")

                with col2:
                    st.markdown("**Field Mapping**")
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
                                any_unmapped = True
                                global_unmapped = True
                        else:
                            any_unmapped = True
                            global_unmapped = True

                    if any_unmapped:
                        st.warning("⚠️ Some required fields have not been mapped.")

    if global_unmapped:
        st.warning("⚠️ Please complete all required field mappings before proceeding.")

    return selected_kpis


def generate_kpi_mapping_summary(selected_kpis, kpis_df, file_data):
    st.header("Step 7: Generate KPI Field Mapping Summary")

    if st.button("Generate Mapping Summary for KPIs"):

        output = io.StringIO()
        output.write("Field Mappings Summary for KPIs:\n\n")

        for _, row in kpis_df[kpis_df['KPI Name'].isin(selected_kpis)].iterrows():
            required_fields = [f.strip() for f in row['Required Fields'].split(";")]

            output.write(f"KPI: {row['KPI Name']}\n")

            for field in required_fields:
                output.write(f"  Field: {field}\n")

                # Search for mapping in session state
                table_key = f"table_choice_{row['KPI Name']}_{field}"
                field_key = f"field_choice_{row['KPI Name']}_{field}"

                table_choice = st.session_state.get(table_key, "-- Select Table --")
                field_choice = st.session_state.get(field_key, "-- Select Field --")

                if table_choice != "-- Select Table --" and field_choice != "-- Select Field --":
                    output.write(f"    Mapped to '{field_choice}' in table '{table_choice}'\n")
                else:
                    output.write("    Unmapped! (Calculation Required)\n")

            output.write("\n")

        st.download_button(
            label="Download KPI Field Mappings Summary as TXT",
            data=output.getvalue(),
            file_name="kpi_field_mappings_summary.txt",
            mime="text/plain"
        )




# Main app
def main():
    st.set_page_config(page_title="Data Relationship Builder", layout="wide")
    st.title("📊 Data Relationship Builder")
    st.markdown("Build and visualize relationships between your uploaded tables, then upload KPIs to complete your model.")

    # 🔐 Initialize session state variables
    if "file_data" not in st.session_state:
        st.session_state.file_data = {}

    if "table_purposes" not in st.session_state:
        st.session_state.table_purposes = {}

    total_steps = 5

    # Step 1
    display_progress(1, total_steps)
    uploaded_files = upload_files()

    if uploaded_files:
        # Step 2
        display_progress(2, total_steps)
        define_table_purposes()

        # Step 3
        display_progress(3, total_steps)
        define_relationships()
        connectivity_check()

        # Step 4
        display_progress(4, total_steps)
 
        show_relationship_summary()  # <--- Must be called
        show_relationship_diagram()

        # Step 5: Load KPI File
        kpis_df = load_kpi_csv()

        if kpis_df is not None:
            # Step 6: KPI Selection and Field Mapping
            selected_kpis = kpi_selection_and_mapping(kpis_df, file_data)

            # Step 7: Generate KPI Field Mapping Summary
            if selected_kpis:
                generate_kpi_mapping_summary(selected_kpis, kpis_df, file_data)


if __name__ == "__main__":
    main()