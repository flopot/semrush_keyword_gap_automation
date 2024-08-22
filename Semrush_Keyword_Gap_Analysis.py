import streamlit as st
import pandas as pd
import re

def main():
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
        
        # Display entered values for debugging
        st.write(f"Categories Input: {categories_input}")
        st.write(f"Use First Directory: {use_first_directory}")

        # Parse categories
        categories = {}
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
        
        # Display entered values for debugging
        st.write(f"Keyword Patterns Input: {patterns_input}")
        st.write(f"Skip Keyword Patterns: {skip_keyword_patterns}")

        # Parse keyword patterns
        patterns = []
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
            csv_list = []
            for uploaded_file in uploaded_files:
                df = pd.read_csv(uploaded_file)
                csv_list.append(df.assign(File_Name=uploaded_file.name))
                st.write(f"Preview of {uploaded_file.name}:")
                st.write(df.head())  # Display first few rows of the DataFrame for preview

            # Merge the DataFrames
            if csv_list:
                csv_merged = pd.concat(csv_list, ignore_index=True)
                st.write("Merged DataFrame Preview:")
                st.write(csv_merged.head())  # Display first few rows of the merged DataFrame

                # Ensure the domain_name column exists
                if domain_name not in csv_merged.columns:
                    st.error(f"Error: The domain '{domain_name}' does not exist in the CSV files.")
                    return

                # Categorize URLs
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
                if pages_column not in csv_merged.columns:
                    st.error(f"Error: The column '{pages_column}' does not exist in the CSV files.")
                    return

                csv_merged['Category'] = csv_merged[pages_column].apply(categorize)

                # Bin the values for status
                bins = [-float('inf'), 0, 3, 10, 30, float('inf')]
                labels = ['missing', '1-3', '4-10', '11-30', '31+']
                csv_merged[domain_name] = pd.to_numeric(csv_merged[domain_name], errors='coerce')
                csv_merged['Status'] = pd.cut(csv_merged[domain_name], bins=bins, labels=labels, right=False)

                # Apply keyword patterns
                if not skip_keyword_patterns:
                    def keyword_patterns(keyword):
                        for regex, label in patterns:
                            if re.search(regex, keyword, re.IGNORECASE):
                                return label
                        return 'non brand'

                    csv_merged['Keyword Patterns'] = csv_merged['Keyword'].apply(keyword_patterns)
                else:
                    csv_merged['Keyword Patterns'] = 'non brand'

                # Remove unnecessary columns
                columns_to_remove = ['Competition', 'Results', 'File_Name']
                csv_merged.drop(columns=columns_to_remove, inplace=True, errors='ignore')

                # Reorder columns
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

                remaining_columns = sorted([col for col in csv_merged.columns if col not in columns_order])
                final_columns_order = columns_order + remaining_columns
                csv_merged = csv_merged[final_columns_order]

                # Sort by search volume
                csv_merged = csv_merged.sort_values(by='Search Volume', ascending=False)

                # Define filtered_data after processing csv_merged
                filtered_data = csv_merged[csv_merged['Category'] != 'Other']

                # Save the processed CSV
                output_filename = 'overall.csv'
                csv_merged.to_csv(output_filename, index=False)
                st.success(f"Processed data saved to {output_filename}")

                # Provide download button for overall.csv
                st.download_button(
                    label="Download overall.csv",
                    data=csv_merged.to_csv(index=False),
                    file_name=output_filename,
                    mime="text/csv"
                )

                # Generate and download pos4to10.csv
                pos4to10 = csv_merged[(csv_merged['Status'] == '4-10') & (csv_merged['Category'] != 'Other') & (csv_merged['Keyword Patterns'] != '')]
                pos4to10 = pos4to10.sort_values(by='Search Volume', ascending=False)
                pos4to10_filename = 'pos4to10.csv'
                pos4to10.to_csv(pos4to10_filename, index=False)
                st.download_button(label="Download pos4to10.csv", data=pos4to10.to_csv(index=False), file_name=pos4to10_filename, mime='text/csv')

                # Generate and download pos11to30.csv
                pos11to30 = csv_merged[(csv_merged['Status'] == '11-30') & (csv_merged['Category'] != 'Other') & (csv_merged['Keyword Patterns'] != '')]
                pos11to30 = pos11to30.sort_values(by='Search Volume', ascending=False)
                pos11to30_filename = 'pos11to30.csv'
                pos11to30.to_csv(pos11to30_filename, index=False)
                st.download_button(label="Download pos11to30.csv", data=pos11to30.to_csv(index=False), file_name=pos11to30_filename, mime='text/csv')

                # Generate and download summary_by_status_category_keyword_pattern.csv
                summary_1 = filtered_data.groupby(['Status', 'Category', 'Keyword Patterns'], observed=False).agg(
                    keyword_count=('Keyword', 'count'),
                    search_volume_sum=('Search Volume', 'sum')
                ).reset_index()

                summary_1 = summary_1[summary_1['keyword_count'] > 0]
                summary_1['% of category'] = summary_1['keyword_count'] / summary_1.groupby('Category')['keyword_count'].transform('sum') * 100
                summary_1['% of search volume'] = summary_1['search_volume_sum'] / summary_1.groupby('Category')['search_volume_sum'].transform('sum') * 100
                summary_1 = summary_1[['Status', 'Category', 'Keyword Patterns', 'keyword_count', '% of category', 'search_volume_sum', '% of search volume']]
                summary_1_filename = 'summary_by_status_category_keyword_pattern.csv'
                summary_1.to_csv(summary_1_filename, index=False)
                st.download_button(label="Download summary_by_status_category_keyword_pattern.csv", data=summary_1.to_csv(index=False), file_name=summary_1_filename, mime='text/csv')

                # Generate and download summary_by_status.csv
                summary_2 = filtered_data.groupby('Status', observed=False).agg(
                    keyword_count=('Keyword', 'count'),
                    search_volume_sum=('Search Volume', 'sum')
                ).reset_index()

                summary_2 = summary_2[summary_2['keyword_count'] > 0]
                summary_2['% of status'] = 100 * summary_2['keyword_count'] / summary_2['keyword_count'].sum()
                summary_2['% of search volume'] = 100 * summary_2['search_volume_sum'] / summary_2['search_volume_sum'].sum()
                summary_2 = summary_2[['Status', 'keyword_count', '% of status', 'search_volume_sum', '% of search volume']]
                summary_2_filename = 'summary_by_status.csv'
                summary_2.to_csv(summary_2_filename, index=False)
                st.download_button(label="Download summary_by_status.csv", data=summary_2.to_csv(index=False), file_name=summary_2_filename, mime='text/csv')

                # Generate and download summary_by_category.csv
                summary_3 = filtered_data.groupby('Category', observed=False).agg(
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
                st.download_button(label="Download summary_by_category.csv", data=summary_3.to_csv(index=False), file_name=summary_3_filename, mime='text/csv')

if __name__ == "__main__":
    main()
