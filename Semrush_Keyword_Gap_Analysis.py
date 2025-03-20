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
    st.title("Semrush Keyword Gap Automation v2.0")
    
    # Step 1: Compile all domains' data
    st.header("Step 1: Upload and Compile All Domains' Data")
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
        
        # Merge and Remove Duplicates
        csv_merged = pd.concat(csv_list, ignore_index=True)
        csv_merged.drop_duplicates(inplace=True)
        
        # Keep Only Required Columns
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
        
        # Extract Domain and Insert it between CPC and Position
        csv_merged.insert(5, "Domain", csv_merged["URL"].apply(extract_domain))
        
        # Remove Duplicates Based on Domain and Keyword (Keep Best Position)
        csv_merged = csv_merged.sort_values(by=["Keyword", "Domain", "Position"], ascending=[True, True, True])
        csv_merged = csv_merged.drop_duplicates(subset=["Keyword", "Domain"], keep="first")
        
        # Save the processed CSV
        output_filename = 'compiled_data.csv'
        csv_merged.to_csv(output_filename, index=False)
        st.success(f"Compiled data saved to {output_filename}")
        
        # Provide download button for compiled data
        if st.download_button(
            label="Download Compiled Data",
            data=csv_merged.to_csv(index=False),
            file_name=output_filename,
            mime="text/csv"
        ):
            st.session_state.next_step = True
    
    # Step 2: Keyword Gap Analysis
    if st.session_state.get("next_step", False):
        st.header("Step 2: Create Keyword Gap Analysis")
        domain_name = st.text_input("Enter Your Domain Name")
        
        if domain_name:
            if domain_name not in csv_merged["Domain"].unique():
                st.error("The provided domain does not exist in the compiled data.")
                return
            
            # Keep Required Columns & Remove Keyword Duplicates
            gap_data = csv_merged[["Keyword", "Keyword Intents", "Search Volume", "Keyword Difficulty", "CPC"]]
            gap_data.drop_duplicates(subset=["Keyword"], keep="first", inplace=True)
            
            # Create Position and URL Columns for Each Domain
            domain_pivot = csv_merged.pivot_table(index="Keyword", columns="Domain", values=["Position", "URL"], aggfunc="first")
            domain_pivot.columns = [f"{domain} {col}" for col, domain in domain_pivot.columns]
            
            # Merge with the main dataset
            gap_data = gap_data.merge(domain_pivot, on="Keyword", how="left")
            
            # Add "Status" Column
            def determine_status(row):
                if pd.isna(row.get(f"{domain_name} Position")):
                    return "Missing"
                best_rank = min([row[col] for col in domain_pivot.columns if "Position" in col and not pd.isna(row[col])])
                if row[f"{domain_name} Position"] == best_rank:
                    return "Strong"
                return "Weak"
                
            gap_data["Status"] = gap_data.apply(determine_status, axis=1)
            
            # Count Domains in Top 30
            position_cols = [col for col in domain_pivot.columns if "Position" in col]
            gap_data["Domains in top 30"] = gap_data[position_cols].apply(lambda x: sum(x <= 30), axis=1)
            
            # Save Keyword Gap Data
            gap_output_filename = "keyword_gap_analysis.csv"
            gap_data.to_csv(gap_output_filename, index=False)
            st.success(f"Keyword gap analysis saved to {gap_output_filename}")
            
            # Provide download button for the keyword gap file
            st.download_button(
                label="Download Keyword Gap Analysis",
                data=gap_data.to_csv(index=False),
                file_name=gap_output_filename,
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
