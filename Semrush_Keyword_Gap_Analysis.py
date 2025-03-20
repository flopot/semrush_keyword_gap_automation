import streamlit as st
import pandas as pd
import re
from urllib.parse import urlparse

def extract_domain(url):
    """Extracts the main domain from a URL (e.g., 'https://www.example.com/page' -> 'example.com')."""
    try:
        parsed_url = urlparse(url)
        domain_parts = parsed_url.netloc.split('.')
        if len(domain_parts) > 2:
            return '.'.join(domain_parts[-2:])  # Keeps only the main domain and TLD
        return parsed_url.netloc
    except:
        return None

def main():
    st.title("Semrush Keyword Gap Automation")
    
    # Step 1: Upload CSV files
    st.header("Upload CSV Files")
    uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type=["csv"])
    
    if uploaded_files:
        csv_list = []
        for uploaded_file in uploaded_files:
            try:
                df = pd.read_csv(uploaded_file, delimiter=';')
                csv_list.append(df)
            except Exception as e:
                st.error(f"Error reading file {uploaded_file.name}: {e}")
                return
        
        # Step 2: Merge and Remove Duplicates
        csv_merged = pd.concat(csv_list, ignore_index=True)
        csv_merged.drop_duplicates(inplace=True)
        
        # Step 3: Keep Only Required Columns
        required_columns = [
            "Keyword", "Keyword Intents", "Search Volume", "Keyword Difficulty",
            "CPC", "Position", "URL", "Position Type"
        ]
        
        # Ensure required columns exist
        missing_columns = [col for col in required_columns if col not in csv_merged.columns]
        if missing_columns:
            st.error(f"Missing required columns: {missing_columns}")
            return
        
        csv_merged = csv_merged[required_columns]
        
        # Step 4: Extract Domain and Insert it between CPC and Position
        csv_merged.insert(5, "Domain", csv_merged["URL"].apply(extract_domain))
        
        # Step 5: Remove Duplicates Based on Domain and Keyword (Keep Best Position)
        csv_merged = csv_merged.sort_values(by=["Keyword", "Domain", "Position"], ascending=[True, True, True])
        csv_merged = csv_merged.drop_duplicates(subset=["Keyword", "Domain"], keep="first")
        
        # Save the processed CSV
        output_filename = 'processed_data.csv'
        csv_merged.to_csv(output_filename, index=False)
        st.success(f"Processed data saved to {output_filename}")
        
        # Provide download button for the final CSV
        st.download_button(
            label="Download Processed CSV",
            data=csv_merged.to_csv(index=False),
            file_name=output_filename,
            mime="text/csv"
        )
        
        # Display Preview
        st.write("Preview of Processed Data:")
        st.write(csv_merged.head())

if __name__ == "__main__":
    main()
