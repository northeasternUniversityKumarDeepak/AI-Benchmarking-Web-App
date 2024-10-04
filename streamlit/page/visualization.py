import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
import matplotlib.pyplot as plt

def show():
# Azure SQL connection 
    driver = st.secrets['driver']
    server = st.secrets['server']
    database = st.secrets['database']
    username = st.secrets['username']
    password = st.secrets['password']

    # Function to fetch data from Azure SQL
    @st.cache_data(ttl=600)  
    def fetch_data_from_azure():
        conn_str = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(conn_str)
        
        # Query your table
        query = "SELECT * FROM ai.metadata"
        df = pd.read_sql(query, conn)
        
        conn.close()
        return df

    # Fetch the data
    df = fetch_data_from_azure()

    # Clean up and convert the data
    df['direct_response'] = df['direct_response'].str.strip()  
    df['annotator_response'] = df['annotator_response'].str.strip() 
    # Convert to numeric, forcing invalid parsing to NaN
    df['direct_response'] = pd.to_numeric(df['direct_response'], errors='coerce')
    df['annotator_response'] = pd.to_numeric(df['annotator_response'], errors='coerce')
    df['task_level'] = pd.to_numeric(df['task_level'], errors='coerce')

    # Drop rows with NaN values in task_level, direct_response, or annotator_response
    df = df.dropna(subset=['direct_response', 'annotator_response', 'task_level'])

    # Convert task_level to integer (if desired)
    df['task_level'] = df['task_level'].astype(int)

    st.header("Interactive Visualizations")

    # Histogram: Distribution of Responses
    st.subheader("Response Distribution by Task Level")
    fig_hist = px.histogram(df, x='task_level', y=['direct_response', 'annotator_response'], 
                            barmode='group', 
                            labels={
                                'task_level': 'Task Level',
                                'value': 'Response Count',
                                'variable': 'Response Type'
                            },
                            title="Response Distribution by Task Level")
    st.plotly_chart(fig_hist)
    
    # Pie Chart: Response Distribution by Task Level
    st.subheader("Response Distribution by Task Level (Pie Chart)")
    task_level_grouped = df.groupby('task_level').agg({
        'direct_response': 'sum',
        'annotator_response': 'sum'
    }).reset_index()

    # Select task level for the pie chart
    task_level = st.selectbox('Select Task Level', task_level_grouped['task_level'].unique())

    # Filter data for selected task level
    filtered_data = task_level_grouped[task_level_grouped['task_level'] == task_level]

    # Plot the pie chart
    labels = ['Direct Response', 'Annotator Response']
    sizes = [filtered_data['direct_response'].values[0], filtered_data['annotator_response'].values[0]]

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=['#ff9999','#66b3ff'])
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    st.pyplot(fig)