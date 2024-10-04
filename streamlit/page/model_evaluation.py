import streamlit as st
import boto3
import json
from dotenv import load_dotenv
import os
import pathlib
from sqlalchemy import create_engine, text
import pyodbc
import openai
import PyPDF2
import pytesseract
import pandas as pd
import plotly.express as px
from PIL import Image
from io import BytesIO
import tiktoken
from IPython import embed

def show():
    env_path = pathlib.Path('.') / '.env'

    load_dotenv(dotenv_path=env_path)

    openai.api_key = st.secrets['OPENAI_API_KEY']

    session = boto3.Session(
        aws_access_key_id = st.secrets['aws_access_key_id'],
        aws_secret_access_key = st.secrets['aws_secret_access_key'],
        region_name='us-east-2'
    )

    s3 = session.client('s3')


    driver = st.secrets['driver']
    server = st.secrets['server']
    database = st.secrets['database']
    username = st.secrets['username']
    password = st.secrets['password']
    connection_string = f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'
    # print(f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}')
    # embed()
    tokenizer = tiktoken.encoding_for_model('gpt-4o')
    MAX_TOKENS = 30000


    # Initialize the S3 client using boto3
    # s3 = boto3.client('s3')
    bucket_name = st.secrets['bucket_name']
    s3_file_key = st.secrets['s3_file_key']
    s3_file_key_path = st.secrets['s3_file_key_path']

    conn = pyodbc.connect(connection_string)


    def count_tokens(text):
        """Counts the number of tokens in the text using the OpenAI tokenizer."""
        return len(tokenizer.encode(text))

    def truncate_prompt(prompt, max_tokens):
        """Truncates the prompt to fit within the allowed token limit."""
        tokens = tokenizer.encode(prompt)
        
        # If prompt tokens exceed the max, truncate it
        if len(tokens) > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            truncated_prompt = tokenizer.decode(truncated_tokens)
            return truncated_prompt
        return prompt

    def download_file_from_s3(bucket_name, s3_file_key):
        try:
            file_obj = s3.get_object(Bucket=bucket_name, Key=s3_file_key)
            file_content = file_obj['Body'].read()
            
            return file_content
        except Exception as e:
            st.error(f"Error downloading file from S3: {e}")
            return None

    # Function to transcribe MP3 file using Whisper API
    def transcribe_audio(mp3_file_content):
        try:
            temp_mp3_path = "/tmp/temp_audio.mp3"
            with open(temp_mp3_path, 'wb') as f:
                f.write(mp3_file_content)

            # Use OpenAI Whisper to transcribe the audio file
            with open(temp_mp3_path, 'rb') as audio_file:
                transcript = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file
                )
            return transcript['text']
        except Exception as e:
            st.error(f"Error transcribing audio: {e}")
            return None

    # Function to extract text from PDF
    def extract_text_from_pdf(pdf_content):
        try:
            reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {e}")
            return None

    # Function to extract text from images using Tesseract OCR
    def extract_text_from_image(image_content):
        try:
            image = Image.open(BytesIO(image_content))
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            st.error(f"Error extracting text from image: {e}")
            return None

    # Function to extract text from Excel files (XLSX)
    def extract_text_from_xlsx(xlsx_content):
        try:
            excel_file = BytesIO(xlsx_content)
            df = pd.read_excel(excel_file)
            text = df.to_string(index=False)
            return text
        except Exception as e:
            st.error(f"Error extracting text from XLSX: {e}")
            return None

    # Function to read Python script (PY) files
    def extract_text_from_python_script(py_file_content):
        try:
            # Simply read the file as text
            return py_file_content.decode('utf-8')
        except Exception as e:
            st.error(f"Error reading Python script: {e}")
            return None

    # Function to extract data from PDB files
    def extract_text_from_pdb(pdb_file_content):
        try:
            pdb_data = pdb_file_content.decode('utf-8')
            # Optionally, you could parse and process the PDB content further
            return pdb_data
        except Exception as e:
            st.error(f"Error extracting data from PDB file: {e}")
            return None
    # Function to download .zip file from S3
    # def download_zip_from_s3(bucket_name, s3_file_key):
    #     try:
    #         # Download the file from S3
    #         file_obj = s3.get_object(Bucket=bucket_name, Key=s3_file_key)
    #         return file_obj['Body'].read()  # Return the binary content of the file
    #     except Exception as e:
    #         st.error(f"Error downloading file from S3: {e}")
    #         return None

    # # Function to extract the contents of the .zip file
    # def extract_zip_contents(zip_content):
    #     extracted_files = {}
    #     try:
    #         # Open the zip file from binary content
    #         with zipfile.ZipFile(BytesIO(zip_content), 'r') as zip_ref:
    #             # Iterate over all the files in the zip archive
    #             for file_info in zip_ref.infolist():
    #                 with zip_ref.open(file_info) as extracted_file:
    #                     # Read the content of each file and store in a dictionary
    #                     extracted_files[file_info.filename] = extracted_file.read()
    #         return extracted_files
    #     except Exception as e:
    #         st.error(f"Error extracting zip file: {e}")
    #         return None

    # Function to determine file type and process accordingly
    def process_file_based_on_extension(file_content, file_extension):
        if file_extension == '.pdf':
            return extract_text_from_pdf(file_content)
        elif file_extension in ['.png', '.jpg', '.jpeg']:
            return extract_text_from_image(file_content)
        elif file_extension == '.mp3':
            return transcribe_audio(file_content)
        elif file_extension == '.py':
            return extract_text_from_python_script(file_content)
        elif file_extension == '.pdb':
            return extract_text_from_pdb(file_content)
        else:
            return file_content



    # Function to insert or update data using pyodbc
    def insert_or_update_metadata(task_id, task_level, direct_response, annotator_response):
        try:
            # Open a cursor
            cursor = conn.cursor()
            
            # Check if the task_id already exists
            select_query = "SELECT task_id FROM ai.metadata WHERE task_id = ?"
            cursor.execute(select_query, (task_id,))
            result = cursor.fetchone()
            # print(result)

            if result:
                # If task_id exists, update the record
                update_query = """
                    UPDATE ai.metadata
                    SET direct_response = CASE WHEN ? = '-1' THEN direct_response ELSE ? END, 
                        annotator_response = ?
                    WHERE task_id = ?
                """
                cursor.execute(update_query, (f'{direct_response}', f'{direct_response}', f'{annotator_response}', f'{task_id}'))
                st.success(f"Task {task_id} updated successfully.")
            else:
                # If task_id doesn't exist, insert a new record
                insert_query = """
                    INSERT INTO ai.metadata (task_id, task_level,direct_response)
                    VALUES (?, ?, ?)
                """
                cursor.execute(insert_query, (f'{task_id}', f'{task_level}',f'{direct_response}'))
                st.success(f"Task {task_id} inserted successfully.")
            
            # Commit the changes
            conn.commit()
        
        except Exception as e:
            st.error(f"Error executing SQL query: {e}")
            conn.rollback()
        finally:
            # Close the cursor after execution
            cursor.close()

    # Function to query OpenAI model with a selected question
    def ask_openai(question, processed_content, file_extension, metadata=None):
        try:
            if processed_content:
                if metadata:
                    prompt = f"Question: {question}\nAnnotator Metadata: {json.dumps(metadata)}.Attached File : {processed_content} with {file_extension}.\n Analyze this file and change to desire format. If unable to analyze, proceed with the othe instructions.\n  Follow these steps to find the answer."
                else:
                    prompt = f"Question: {question}.\n Attached File : {processed_content} with {file_extension}. Analyze this file and change to desire format. If unable to analyze, proceed with the othe instructions."
            else:
                if metadata:
                    prompt = f"Question: {question}\nAnnotator Metadata: {json.dumps(metadata)}"
                else:
                    prompt = f"Question: {question}"

            # print(prompt)
            # st.write(prompt)
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt+"provide only final answer"}
                ],
                max_tokens=1500
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            st.error(f"Error querying OpenAI: {e}")
            return None

    # Function to fetch the .jsonl file from S3
    def load_jsonl_from_s3(bucket_name, s3_file_key):
        try:
            file_obj = s3.get_object(Bucket=bucket_name, Key=s3_file_key)
            
            file_content = file_obj['Body'].read().decode('utf-8')
            json_lines = [json.loads(line) for line in file_content.strip().split('\n')]
            
            df = pd.DataFrame(json_lines)
            
            return df
        except Exception as e:
            st.error(f"Error loading data from S3: {e}")
            return None

    # Streamlit app layout
    st.title("Ask Anything")

    # Load the metadata from S3
    metadata_df = load_jsonl_from_s3(bucket_name, s3_file_key)

    if metadata_df is not None:
        questions = [''] + metadata_df['Question'].tolist()
        selected_question = st.selectbox("Choose a Question", options=questions)
        if selected_question:
            selected_task_df = metadata_df[metadata_df['Question'] == selected_question]
            if not selected_task_df.empty:
                selected_task = metadata_df[metadata_df['Question'] == selected_question].iloc[0]
                annotator_metadata = selected_task['Annotator Metadata']
                task_level = selected_task['Level']
                task_id = selected_task['task_id']
                final_answer = selected_task['Final answer']
                file_path = s3_file_key_path + selected_task['file_name'] if selected_task['file_name'] else None
                # print(file_path)
                processed_content = None
                file_extension = None
                if file_path:
                    # Download the file from S3
                    file_content = download_file_from_s3(bucket_name, file_path)
                    # Get the file extension
                    file_extension = os.path.splitext(file_path)[1].lower()
                    # print(file_extension)
                    if file_content and file_extension:
                        processed_content = process_file_based_on_extension(file_content, file_extension)
                        prompt_token_count = count_tokens(processed_content) if file_extension in ['.png', '.jpg', '.jpeg', '.pdf','.mp3','.pdb'] else 0
                        if prompt_token_count > MAX_TOKENS:
                            processed_content = truncate_prompt(processed_content, MAX_TOKENS)
                st.write(f"Expected Output : {final_answer}")

                if st.button("Submit"):
                    if selected_question:
                        with st.spinner("Waiting for OpenAI response..."):
                            
                            openai_response = ask_openai(selected_question, processed_content, file_extension)
                            insert_or_update_metadata(task_id, task_level, '1' if final_answer.lower() in openai_response.lower() else '0', '0')
                            if openai_response:

                                st.write(f"OpenAI Response: {openai_response}")
                            else:
                                st.error("Failed to get a response from OpenAI.")
                    else:
                        st.error("Please select a question first.")
                
                if st.button("Try Again"):
                    if selected_question:
                        with st.spinner("Waiting for OpenAI response with annotator metadata..."):
                            openai_response_with_metadata = ask_openai(selected_question, processed_content, file_extension, metadata=annotator_metadata)
                            insert_or_update_metadata(task_id, task_level, '-1', '1' if final_answer.lower() in openai_response_with_metadata.lower() else '0')

                            if openai_response_with_metadata:
                                st.write(f"OpenAI Response with Metadata: {openai_response_with_metadata}")
                            else:
                                st.error("Failed to get a response from OpenAI.")
                    else:
                        st.error("Please select a question first.")
    @st.cache_data(ttl=600)  # cache data for 10 minutes
    def fetch_data_from_azure():
        
        # Query your table
        query = "SELECT * FROM ai.metadata"
        df = pd.read_sql(query, conn)
        
        conn.close()
        return df
    df = fetch_data_from_azure()
    df['task_level'] = pd.to_numeric(df['task_level'], errors='coerce')

    # Drop rows with NaN values in task_level
    df = df.dropna(subset=['task_level'])

    # Convert task_level to integer
    df['task_level'] = df['task_level'].astype(int)

    # Line chart: Direct Response vs Annotator Response over Task IDs
    st.subheader("Response Trends Over Task IDs")
    fig_line = px.line(df, x='metadata_sk', y=['direct_response', 'annotator_response'], 
                    labels={
                        'metadata_sk': 'Task ID',
                        'value': 'Response Count',
                        'variable': 'Response Type'
                    },
                    title="Direct Response vs Annotator Response Across Task IDs")
    st.plotly_chart(fig_line)