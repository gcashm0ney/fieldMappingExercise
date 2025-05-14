import streamlit as st
import pandas as pd
import io

# Title
st.title("Data Model Relationship Definition")

# Step 1: Multi-file Upload with Dynamic Start Row Option
uploaded_files = st.file_uploader("Upload multiple CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    # Create a dictionary to store each file's data and its user-defined name
    file_data = {}
    
    for file in uploaded_files:
        file_name = st.text_input(f"Enter a name for the file '{file.name}'", value=file.name.split('.')[0])
        start_row = st.selectbox(f"Select the row where headers start for '{file_name}'", options=range(1, 11), index=7)
        
        # Read the file with dynamic start row
        df = pd.read_csv(file, skiprows=start_row-1)
        
        file_data[file_name] = {"df": df, "start_row": start_row}

    st.success(f"{len(uploaded_files)} file(s) uploaded successfully!")

else:
    st.stop()

# Step 2: Select Key Fields and Define Relationships
st.header("Define Relationships Between Tables")

# Create a list to store user-defined relationships
relationships = []

# Loop over each file to display their columns for key field selection
for file_name, data in file_data.items():
    st.subheader(f"File: {file_name}")
    file_columns = data["df"].columns.tolist()
    
    # Display key fields dropdown
    key_field = st.selectbox(f"Select key field for '{file_name}' (e.g., ProductID, CustomerID)", options=["-- Select --"] + file_columns, key=f"key_field_{file_name}")
    
    if key_field != "-- Select --":
        # List other files to match against
        other_files = [f for f in file_data if f != file_name]  # Get other files to match against
        
        # Display relationship type dropdown
        relationship_type = st.selectbox(f"Select relationship type for '{key_field}'", options=["One-to-Many", "Many-to-One", "One-to-One", "Many-to-Many"], key=f"relationship_{file_name}_{key_field}")
        
        # Let the user choose the related field in another file
        related_file = st.selectbox(f"Select related file for '{key_field}'", options=other_files, key=f"related_file_{file_name}_{key_field}")
        related_columns = file_data[related_file]["df"].columns.tolist()
        
        related_key = st.selectbox(f"Select key field in '{related_file}' that matches '{key_field}'", options=related_columns, key=f"related_key_{file_name}_{key_field}")
        
        # Store the relationship if all details are provided
        if relationship_type and related_key:
            relationships.append({
                "Source File": file_name,
                "Source Field": key_field,
                "Relationship Type": relationship_type,
                "Target File": related_file,
                "Target Field": related_key
            })

# Step 3: Display and Confirm the Relationships
st.header("Confirmed Relationships")

if relationships:
    relationships_df = pd.DataFrame(relationships)
    st.dataframe(relationships_df)

    # Step 4: Download Mapping Summary
    if st.button("Generate Mapping Summary"):
        output = io.StringIO()
        output.write("Confirmed Field Relationships:\n")
        
        for _, row in relationships_df.iterrows():
            output.write(f"Source File: {row['Source File']} - Field: {row['Source Field']} -> Mapped File: {row['Target File']} - Field: {row['Target Field']} | Relationship Type: {row['Relationship Type']}\n")
        
        st.download_button(
            label="Download Relationship Summary as TXT",
            data=output.getvalue(),
            file_name="data_model_relationships.txt",
            mime="text/plain"
        )
else:
    st.warning("No relationships confirmed yet.")
