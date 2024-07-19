import pandas as pd
import re
import streamlit as st

# Global variables to store user inputs
domain_name = ""
categories = {}
patterns = []
use_first_directory = False
skip_keyword_patterns = False

def input_domain_name():
    global domain_name
    domain_name = st.text_input("Enter domain:", placeholder="example.com")
    if st.button("Validate Domain"):
        if domain_name:
            st.success(f"Domain name '{domain_name}' has been validated.")
            input_categories()

def input_categories():
    global use_first_directory, categories
    category_input = st.text_input("Enter categories:", placeholder="Blog: example.com/blog/, Product: example.com/product")
    if st.button("Validate Categories"):
        categories = {}
        input_text = category_input.strip()
        category_pairs = input_text.split(',')
        for pair in category_pairs:
            try:
                category, regex = pair.split(':', 1)  # Split only on the first ':'
                categories[category.strip()] = regex.strip()
            except ValueError:
                st.error(f"Invalid format for pair: {pair}")
                return
        use_first_directory = False
        st.success(f"Categories have been validated: {categories}")
        input_keyword_patterns()

    if st.button("Skip and use directories"):
        use_first_directory = True
        st.success("Using first directory for categorization.")
        input_keyword_patterns()

def input_keyword_patterns():
    global patterns, skip_keyword_patterns
    patterns_input = st.text_input("Enter keyword patterns:", placeholder="Brand: amazon, Non-brand: .*")
    if st.button("Validate Keyword Patterns"):
        patterns = []
        input_text = patterns_input.strip()
        pattern_pairs = input_text.split(',')
        for pair in pattern_pairs:
            try:
                label, regex = pair.split(':', 1)  # Split only on the first ':'
                patterns.append((regex.strip(), label.strip()))
            except ValueError:
                st.error(f"Invalid format for pair: {pair}")
                return
        skip_keyword_patterns = False
        st.success(f"Keyword patterns have been validated: {patterns}")
        run_script()

    if st.button("Skip Keyword Patterns"):
        skip_keyword_patterns = True
        st.success("Skipping keyword patterns categorization.")
        run_script()

def run_script():
    uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)
    if uploaded_files:
        file_list = [file.name for file in uploaded_files]
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
        st.download_button(label="Download overall.csv", data=output_filename, file_name=output_filename, mime='text/csv')

        pos4to10 = csv_no_duplicates[(csv_no_duplicates['Status'] == '4-10') & (csv_no_duplicates['Category'] != 'Other') & (csv_no_duplicates['Keyword Patterns'] != '')]
        pos4to10 = pos4to10.sort_values(by='Search Volume', ascending=False)
        pos4to10_filename = 'pos4to10.csv'
        pos4to10.to_csv(pos4to10_filename, index=False)
        st.download_button(label="Download pos4to10.csv", data=pos4to10_filename, file_name=pos4to10_filename, mime='text/csv')

        pos11to30 = csv_no_duplicates[(csv_no_duplicates['Status'] == '11-30') & (csv_no_duplicates['Category'] != 'Other') & (csv_no_duplicates['Keyword Patterns'] != '')]
        pos11to30 = pos11to30.sort_values(by='Search Volume', ascending=False)
        pos11to30_filename = 'pos11to30.csv'
        pos11to30.to_csv(pos11to30_filename, index=False)
        st.download_button(label="Download pos11to30.csv", data=pos11to30_filename, file_name=pos11to30_filename, mime='text/csv')

        filtered_data = csv_no_duplicates[csv_no_duplicates['Category'] != 'Other']

        summary_1 = filtered_data.groupby(['Status', 'Category', 'Keyword Patterns']).agg(
            keyword_count=('Keyword', 'count'),
            search_volume_sum=('Search Volume', 'sum')
        ).reset_index()

        summary_1 = summary_1[summary_1['keyword_count'] > 0]

        summary_1['% of category'] = summary_1['keyword_count'] / summary_1.groupby('Category')['keyword_count'].transform('sum') * 100
        summary_1['% of search volume'] = summary_1['search_volume_sum'] / summary_1.groupby('Category')['search_volume_sum'].transform('sum') * 100

        summary_1 = summary_1[['Status', 'Category', 'Keyword Patterns', 'keyword_count', '% of category', 'search_volume_sum', '% of search volume']]
        summary_1_filename = 'summary_by_status_category_keyword_pattern.csv'
        summary_1.to_csv(summary_1_filename, index=False)
        st.download_button(label="Download summary_by_status_category_keyword_pattern.csv", data=summary_1_filename, file_name=summary_1_filename, mime='text/csv')

        summary_2 = filtered_data.groupby('Status').agg(
            keyword_count=('Keyword', 'count'),
            search_volume_sum=('Search Volume', 'sum')
        ).reset_index()

        summary_2 = summary_2[summary_2['keyword_count'] > 0]

        summary_2['% of status'] = 100 * summary_2['keyword_count'] / summary_2['keyword_count'].sum()
        summary_2['% of search volume'] = 100 * summary_2['search_volume_sum'] / summary_2['search_volume_sum'].sum()

        summary_2 = summary_2[['Status', 'keyword_count', '% of status', 'search_volume_sum', '% of search volume']]
        summary_2_filename = 'summary_by_status.csv'
        summary_2.to_csv(summary_2_filename, index=False)
        st.download_button(label="Download summary_by_status.csv", data=summary_2_filename, file_name=summary_2_filename, mime='text/csv')

        summary_3 = filtered_data.groupby('Category').agg(
            keyword_count=('Keyword', 'count'),
            search_volume_sum=('Search Volume', 'sum')
        ).reset_index()

        summary_3 = summary_3[summary_3['keyword_count'] > 0]

        summary_3['% of category'] = 100 * summary_3['keyword_count'] / summary_3['keyword_count'].sum()
        summary_3['% of search volume'] = 100 * summary_3['search_volume_sum'] / summary_3['search_volume_sum'].sum()

        summary_3 = summary_3.sort_values(by='keyword_count', ascending=False)
        summary_3 = summary_3[['Category', 'keyword_count', '% of category', 'search_volume_sum', '% of search volume']]
        summary_3_filename = 'summary_by_category.csv'
        summary_3.to_csv(summary_3_filename, index=False)
        st.download_button(label="Download summary_by_category.csv", data=summary_3_filename, file_name=summary_3_filename, mime='text/csv')

# Run the input prompt for the domain name
st.title("Semrush Keyword GAp Analysis")
input_domain_name()
