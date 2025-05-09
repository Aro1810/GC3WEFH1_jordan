import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sb
from pandasai.llm import GoogleGemini
from pandasai import SmartDataframe
import os

# LLM integration (Google Gemini setup)
gemini_api_key = os.environ.get('gemini')  # Make sure your API key is stored as an environment variable
llm = GoogleGemini(api_key=gemini_api_key, model = "models/gemini-1.5-pro")

def generate_llm_response(dataFrame, prompt):
    pandas_agent = SmartDataframe(dataFrame, config={"llm": llm})
    answer = pandas_agent.chat(prompt)
    return answer

# Title of the app
st.title("Dataset Analysis with Streamlit and Google Gemini LLM")

# Define dataset paths
datasets = {
    'indicator_df': 'jordan_indicadors.csv',
    'governorate_csv': 'dataset/Average Household Size in Jordan/governorate.csv',
    'country_csv': 'dataset/Average Household Size in Jordan/country.csv',
    'para_csv': 'dataset/Average Household Size in Jordan/para.csv',
    'spi_data': '170/SPI_JMD_data_corrected_long_format.csv',
    'healthcare_facilities_csv': 'dataset/Healthcare Facilities in Jordan/healthcare.csv',
    'governorates_jordan_csv': 'dataset/Jordan Health/Governorates_jordan.csv',
    'hospitals_csv': 'dataset/Jordan Health/Hospitals.csv',
    'governorate_boundaries_csv': 'dataset/Jordan Boundaries/governorate.csv',
    'country_boundaries_csv': 'dataset/Jordan Boundaries/country.csv',
    'health_activities_csv': 'dataset/Jordan Health Map/JCAP.csv',
    'country_schema_csv': 'datasets/country_schema.csv',
    'admin_shapefile': 'jordan_admin_regions.shp'
}

# Load dataset functions
def load_csv_dataset(path):
    return pd.read_csv(path)

def load_geodataframe(path):
    return gpd.read_file(path)

# Dropdown to select a dataset from predefined datasets
st.subheader("Select a predefined dataset or upload your own")
dataset_choice = st.selectbox("Choose a Dataset", ["None"] + list(datasets.keys()))

# Upload a custom CSV file
uploaded_file = st.file_uploader("Or upload a CSV file", type="csv")

# Load selected dataset
if dataset_choice != "None":
    # Load from predefined datasets
    if dataset_choice in datasets:
        df = load_csv_dataset(datasets[dataset_choice])
else:
    # Load from uploaded file
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)

# Proceed if a dataset is loaded
if 'df' in locals():
    # Filter for numeric variables
    numeric_vars = [col for col in df.columns if df[col].dtype in [np.float64, np.int64]]

    # **LLM Interaction Section**
    st.subheader("Ask LLM to Describe the Relationship Between Two Variables")

    # Select numeric variables for LLM description
    x_var = st.selectbox("Select X variable", numeric_vars)
    y_var = st.selectbox("Select Y variable", numeric_vars)
    
    if x_var and y_var and x_var != y_var:
        # Calculate descriptive statistics for relationship
        corr = df[[x_var, y_var]].corr().iloc[0, 1]
        x_mean, y_mean = df[x_var].mean(), df[y_var].mean()
        x_sd, y_sd = df[x_var].std(), df[y_var].std()

        # Calculate additional statistics for distribution and outliers
        x_skew, y_skew = df[x_var].skew(), df[y_var].skew()
        x_outliers = df[x_var][(df[x_var] > (x_mean + 2 * x_sd)) | (df[x_var] < (x_mean - 2 * x_sd))].count()
        y_outliers = df[y_var][(df[y_var] > (y_mean + 2 * y_sd)) | (df[y_var] < (y_mean - 2 * y_sd))].count()
        
        # Combine the relationship analysis with distribution, spikes, and outliers in the prompt
        prompt = (
            f"Variable X represents {x_var} and Variable Y represents {y_var}. "
            f"The Pearson correlation coefficient between them is {corr:.2f}. "
            f"Variable X has a mean of {x_mean:.2f} and a standard deviation of {x_sd:.2f}, "
            f"while Variable Y has a mean of {y_mean:.2f} and a standard deviation of {y_sd:.2f}. "
            f"Can you describe the relationship between these variables? "
            f"Please do not generate any images, code, or visual outputs, and only provide a text-based analysis."
        )

        # Generate LLM response
        llm_response = generate_llm_response(df, prompt)
        
        # Display LLM response
        st.write("### LLM-Generated Description:")
        st.write(llm_response)

    # Scatterplot with regression line
    st.subheader("Scatterplot with Regression Line")

    if x_var and y_var and x_var != y_var:
        fig, ax = plt.subplots()
        sb.regplot(x=df[x_var], y=df[y_var], scatter_kws={"s": 20, "color": "red", "alpha": 0.2}, ax=ax)
        ax.set(xlabel=x_var, ylabel=y_var)
        st.pyplot(fig)
    else:
        st.error("X and Y variables must be different!")

    # **Scatter Matrix Section with LLM Analysis**
    st.subheader("Scatter Matrix")
    selected_vars = st.multiselect("Select up to 5 variables for scatter matrix", numeric_vars, numeric_vars[:5])

    # Check for variables with sufficient unique data
    valid_vars = [col for col in selected_vars if df[col].nunique() > 1]

    if valid_vars:
        scatter_matrix_df = df[valid_vars].dropna()  # Remove rows with missing data
        
        if not scatter_matrix_df.empty:
            scatter_matrix_fig = pd.plotting.scatter_matrix(scatter_matrix_df, alpha=0.2, figsize=(10, 10), diagonal='hist')  # Use histograms instead of KDE
            for ax in scatter_matrix_fig.ravel():
                ax.set_xlabel(ax.get_xlabel(), fontsize=10, rotation=90)
                ax.set_ylabel(ax.get_ylabel(), fontsize=10, rotation=0)
            st.pyplot(plt)

            # Generate a prompt for the LLM to analyze the scatter matrix
            prompt = (
                f"A scatter matrix has been generated for the variables {', '.join(valid_vars)}. "
                f"Please provide insights on the relationships between these variables. "
                f"Are there any strong correlations, clusters, or patterns? "
                f"Do you observe any outliers or unusual distributions in these pairwise plots? "
                f"Please do not generate any images, code, or visual outputs, and only provide a text-based analysis."
            )

            # Generate LLM response for scatter matrix analysis
            llm_response_scatter_matrix = generate_llm_response(df[valid_vars], prompt)
            
            # Display LLM response for scatter matrix
            st.write("### LLM-Generated Analysis for Scatter Matrix:")
            st.write(llm_response_scatter_matrix)
        else:
            st.error("The selected variables contain too many missing values to generate a scatter matrix.")
    else:
        st.error("None of the selected variables have enough data to plot a scatter matrix.")

    # Descriptive statistics
    st.subheader("Descriptive Statistics")
    selected_stat_var = st.selectbox("Select a variable to calculate statistics", numeric_vars)

    if selected_stat_var:
        var = df[selected_stat_var]
        vmean = var.mean()
        vsd = var.std()
        vskew = var.skew()
        vvar = var.var()

        st.write(f"**Mean:** {vmean}")
        st.write(f"**Standard Deviation:** {vsd}")
        st.write(f"**Variance:** {vvar}")
        st.write(f"**Skew:** {vskew}")

        # Histogram
        fig, ax = plt.subplots()
        var.hist(ax=ax)
        ax.axvline(vmean, color='red', linestyle='dashed', linewidth=2)
        ax.set_xlabel(selected_stat_var)
        st.pyplot(fig)

        # Generate LLM prompt for statistics
        prompt = (
            f"The selected variable is {selected_stat_var}. "
            f"It has a mean of {vmean:.2f}, a standard deviation of {vsd:.2f}, a variance of {vvar:.2f}, "
            f"and a skewness of {vskew:.2f}. Please describe the distribution of the variable, identify any sharp spikes, and discuss possible outliers. "
            f"Please do not generate any images, code, or visual outputs, and only provide a text-based analysis."
        )

        # Generate LLM response for descriptive statistics
        llm_response_stats = generate_llm_response(df, prompt)
        
        # Display LLM response for descriptive statistics
        st.write("### LLM-Generated Description for Descriptive Statistics:")
        st.write(llm_response_stats)

else:
    st.write("Please select a dataset or upload a CSV file to proceed.")
