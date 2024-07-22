import streamlit as st
import pandas as pd
import re

# Global variables to store user inputs
domain_name = ""
categories = {}
patterns = []
use_first_directory = False
skip_keyword_patterns = False

def main():
    global domain_name, categories, patterns, use_first_directory, skip_keyword_patterns

    st.title("Semrush Keyword Gap Automation")

    # Step 1: Input domain name
    st.header("Step 1: Enter Domain Name")
    domain_name = st.text_input("Domain Name (e.g., example.com)")
    
    if domain_name:
        st.success(f"Domain name '{domain_name}' has been validated.")
        
        # Step 2: Input categories
        st.header("Step 2: Enter Categories")
        categories_input = st.text_input("Categories (e.g., Blog: example.com/blog/, Product: example.com/product)")
        use_first_directory = st.checkbox("Use first directory for categorization instead", value=False)
        
        if categories_input and not use_first_directory:
            category_pairs = categories_input.split(',')
            for pair in category_pairs:
                try:
                    category, regex = pair.split(':', 1)  # Split only on the first ':'
                    categories[category.strip()] = regex.strip()
                except ValueError:
                    st.error(f"Invalid format for pair: {pair}")
                    return
            st.success(f"Categories have been validated: {categories}")
        elif use_first_directory:
            st.success("Using first directory for categorization.")

        # Step 3: Input keyword patterns
        st.header("Step 3: Enter Keyword Patterns")
        patterns_input = st.text_input("Keyword Patterns (e.g., Brand: amazon, Non-brand: .*)")
        skip_keyword_patterns = st.checkbox("Skip keyword patterns categorization", value=False)
        
        if patterns_input and not skip_keyword_patterns:
            pattern_pairs = patterns_input.split(',')
            for pair in pattern_pairs:
                try:
                    label, regex = pair.split(':', 1)  # Split only on the first ':'
                    patterns.append((regex.strip(), label.strip()))
                except ValueError:
                    st.error(f"Invalid format for pair: {pair}")
                    return
            st.success(f"Keyword patterns have been validated: {patterns}")
        elif skip_keyword_patterns:
            st.success("Skipping keyword patterns categorization.")
        
        # Step 4: Upload CSV files
        st.header("Step 4: Upload CSV Files")
        uploaded_files = st.file_uploader("Choose CSV files", accept_multiple_files=True, type=["csv"])
        
        if uploaded_files:
            run_script(uploaded_files)

def run_script(uploaded_files):
    global domain_name, categories, patterns, use_first_directory, skip_keyword_patterns

    csv_list = []

    for uploaded_file in uploaded_files:
        df = pd.read_csv(uploaded_file)
        csv_list.append(df.assign(File_Name=uploaded_file.name))

    csv_merged = pd.concat(csv_list, ignore_index=True)

    if domain_name not in csv_merged.columns:
        st.error(f"Error: The domain '{domain_name}' does not exist in the CSV files.")
        return

    csv_merged[domain_name] = pd.to_numeric(csv_merged[domain_name], errors='coerce')
    csv_no_duplicates = csv_merged.sort_values(domain_name).drop_duplicates(subset='Keyword', keep='first')

    def categorize(page_url):
        if use_first_directory:
            if pd.notnull(page_url):
                first_directory = page_url.split('/')[3] if len(page_url.split('/')) > 3 else 'Other'
                return first_directory
        else:
            if pd.notnull(page_url):
                for category, regex in categories.items():
                    if re.search(regex, page_url):
                        return category
        return 'Other'

    pages_column = f'{domain_name} (pages)'
    if pages_column not in csv_no_duplicates.columns:
        st.error(f"Error: The column '{pages_column}' does not exist in the CSV files.")
        return

    csv_no_duplicates['Category'] = csv_no_duplicates[pages_column].apply(categorize)

    bins = [0, 3, 10, 30, float('inf')]
    labels = ['1-3', '4-10', '11-30', '31+']
    csv_no_duplicates[domain_name] = pd.to_numeric(csv_no_duplicates[domain_name], errors='coerce')
    csv_no_duplicates['Status'] = pd.cut(csv_no_duplicates[domain_name], bins=bins, labels=labels, right=False)

    if not skip_keyword_patterns:
        def keyword_patterns(keyword):
            for regex, label in patterns:
                if re.search(regex, keyword, re.IGNORECASE):
                    return label
            return 'non brand'

        csv_no_duplicates['Keyword Patterns'] = csv_no_duplicates['Keyword'].apply(keyword_patterns)
    else:
        csv_no_duplicates['Keyword Patterns'] = 'non brand'

    columns_to_remove = ['Competition', 'Results', 'File_Name']
    csv_no_duplicates.drop(columns=columns_to_remove, inplace=True)

    columns_order = [
        'Keyword',
        'Category',
        'Keyword Patterns',
        'Status',
        'Search Volume',
        'Keyword Difficulty',
        'CPC',
        'Keyword Intents',
        domain_name,
        pages_column
    ]

    remaining_columns = sorted([col for col in csv_no_duplicates.columns if col not in columns_order])
    final_columns_order = columns_order + remaining_columns
    csv_no_duplicates = csv_no_duplicates[final_columns_order]

    csv_no_duplicates = csv_no_duplicates.sort_values(by='Search Volume', ascending=False)
    output_filename = 'overall.csv'
    csv_no_duplicates.to_csv(output_filename, index=False)
    st.success(f"Processed data saved to {output_filename}")
    st.download_button("Download overall.csv", data=csv_no_duplicates.to_csv(index=False), file_name=output_filename, mime="text/csv")
