


uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    try:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, skiprows=6)
        st.success("File successfully uploaded and read!")
        st.write(df.head())
    except Exception as e:
        st.error(f"Error reading CSV file: {e}")




