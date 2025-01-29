import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import io
import ast
import spacy
from spacy import displacy
import random
import requests
 
# Azure GPT-based response generation
def generate_response_gpt(prompt):
   url = "https://ragemrmodels.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview"
   headers = {
       "Content-Type": "application/json",
       "api-key": '25d8e7bba6844d91ae5df784437a7f0b'
   }
   data = {
       "messages": [
           {"role": "system", "content": "You are a helpful assistant."},
           {"role": "user", "content": prompt}
       ],
       "temperature": 0.2,
   }
   response = requests.post(url, headers=headers, json=data)
   if response.status_code != 200:
       raise Exception(f"Request failed with status code {response.status_code}: {response.text}")
   return response.json()['choices'][0]['message']['content']
 
# Azure Blob Storage Configuration
AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=ragemr;AccountKey=AF+HyEnG71UZ9riNXVseVkmJarlLTZk/5QZjsTWU1RyU9PfyOH8cAt/dVmB1akXzbtAJ7AVT/+2x+AStu71CNg==;EndpointSuffix=core.windows.net'
CONTAINER_NAME = "response"
 
# Map user types to their respective file paths in Azure Blob Storage
user_files = {
   "Patients": {
       "Summary": "Medical_Summary_for_Patients.xlsx",
       "Topic-Wise Summary": "patient_summary_topicwise.xlsx",
       "Admit History": "Admit_History_and_FollowUp.xlsx",
       "Date Relevant Details": "Date_Relevant Details.xlsx"
   },
   "Physicians": {
       "Summary": "Medical_Summary_for_Physician.xlsx",
       "Topic-Wise Summary": "physician_summary_topicwise.xlsx",
       "Discharge Summary": "discharge_summary.xlsx"
   },
   "Specialists": {
       "Summary": "Medical_Summary_for_Specialist.xlsx",
       "Topic-Wise Summary": "specialist_summary_topicwise.xlsx"
   },
   "Patient 360": {
       "Summary": "patient_360_summary.xlsx",
       "Data": "patient_360.xlsx"
   }
}
# Function to read data from Azure Blob Storage
st.set_page_config(layout="wide")
@st.cache_data
 
def read_data_from_blob(file_path):
   blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
   blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file_path)
   download_stream = blob_client.download_blob()
   file_content = io.BytesIO(download_stream.readall())
   data = pd.read_excel(file_content)
   return data
 
# Function to clean up text
def clean_text(text):
   if isinstance(text, str):
       return text.replace('\r', '').replace('\n', '').replace('x000D', '').strip()
   return text
# Function to process text with GPT and SpaCy
def extract_entities_with_gpt_and_spacy(text):
   prompt_template = """Extract entities from the following text and classify them into categories such as
   demographics, geography, family history, vital signs, social determinants, chronic conditions,
   medical condition, symptoms, social support, vaccination records, economic barriers,
   medication, lab result, procedure, symptom.
   "Provide the output as a Python list of tuples in the format [('entity', 'category'), ...].\n\n
   STRICT GUIDELINES:DO NOT ADD ANY TEXT LIKE PYTHON WORD  IN RESPONSE  give in [('entity', 'category'), ...] "
   Text:\n{text}"""
   response = generate_response_gpt(prompt_template.format(text=text))
   try:
       gpt_entities = ast.literal_eval(response.strip())
   except Exception as e:
       st.error(f"Error parsing GPT response: {e}")
       gpt_entities = []
   nlp = spacy.blank("en")
   doc = nlp(text)
   new_spans = []
   occupied_tokens = set()
   for entity_text, entity_label in gpt_entities:
       start = text.lower().find(entity_text.lower())
       if start != -1:
           end = start + len(entity_text)
           span = doc.char_span(start, end, label=entity_label)
           if span:
               span_tokens = set(range(span.start, span.end))
               if not span_tokens & occupied_tokens:
                   new_spans.append(span)
                   occupied_tokens.update(span_tokens)
   doc.ents = new_spans
   entity_types = list(set(span.label_ for span in new_spans))
   colors = {entity: f"#{random.randint(128, 255):02X}{random.randint(128, 255):02X}{random.randint(128, 255):02X}" for entity in entity_types}
   options = {"ents": entity_types, "colors": colors}
   return doc, options
 
# Add custom CSS
def add_custom_css():
   st.markdown(
       """
<style>
   body {
       background: linear-gradient(to bottom, #eef2f6, #c8dff0);
   }
   .block-container {
       background-color: #f7fbff;
       border-radius: 15px;
       padding: 2rem;
       box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
   }
   .custom-header {
       font-size: 18px;
       color: #34495e;
       font-weight: bold;
       text-align: center;
       padding: 10px;
       background-color: #cbe2fa;
       border-radius: 8px;
       margin-bottom: 10px;
   }
   .custom-section {
       margin-bottom: 1rem;
       font-size: 16px;
       color: #2c3e50;
   }
   .styled-table {
       font-family: 'Arial', sans-serif;
       border-collapse: collapse;
       width: 100%;
       margin: 20px 0;
       font-size: 16px;
       text-align: left;
   }
   .styled-table th {
       background-color: #f0f8ff;
       color: #000;
       font-weight: bold;
       padding: 8px;
   }
   .styled-table td {
       border: 1px solid #ddd;
       padding: 8px;
   }
   .styled-table tr:nth-child(even) {
       background-color: #f9f9f9;
   }
</style>
       """,
       unsafe_allow_html=True
   )
 
# Apply custom styling
add_custom_css()
 
# Streamlit App
st.title("🌟 DAI LLM Suite Explorer")
st.markdown(
   """
Welcome to the **DAI LLM Suite Explorer**! Navigate through the dropdown menus to access detailed **medical summaries**, **topic-wise insights**, and more for Patients, Physicians, and Specialists. Additionally, explore in-depth Patient 360 data for a comprehensive view of patient care and health records.
   """
)
 
# Step 1: Select User
user_options = {
   "Patients 👤": "Patients",
   "Physicians 🩺": "Physicians",
   "Specialists 🥼": "Specialists",
   "Patient 360 🌎": "Patient 360"
}
user = st.selectbox("🚀 Select User Type", list(user_options.keys()))
selected_user = user_options[user]
 
# Step 2: Select Module
module_options = list(user_files[selected_user].keys())
if selected_user == "Physicians" and "Discharge Summary" not in user_files[selected_user]:
   user_files[selected_user]["Discharge Summary"] = "discharge_summary.xlsx"
module_options = list(user_files[selected_user].keys())
selected_module = st.selectbox("📂 Select a Module", module_options)
if selected_module:
   file_path = user_files[selected_user][selected_module]
   data = read_data_from_blob(file_path)
   if selected_module == "Summary":
       if 'Response' in data.columns:
           text = " ".join(data['Response'].dropna().apply(clean_text))
           doc, options = extract_entities_with_gpt_and_spacy(text)
           html = displacy.render(doc, style="ent", options=options)
           st.markdown(html, unsafe_allow_html=True)
       else:
           st.error("The selected dataset does not contain a 'Response' column.")
   elif selected_module == "Topic-Wise Summary":
       st.markdown(f"<div class='custom-header'>Topic-Wise Summary for {selected_user}</div>", unsafe_allow_html=True)
       for column in data.columns:
           st.markdown(f"<div class='custom-header'>{column}</div>", unsafe_allow_html=True)
           topic_content = '<br>'.join(data[column].dropna().astype(str))
           styled_content = f"<div class='custom-section'>{topic_content}</div>"
           st.markdown(styled_content, unsafe_allow_html=True)
   elif selected_module == "Admit History":
       st.markdown("<div class='custom-header'>Admit History and Follow-Up</div>", unsafe_allow_html=True)
       data["Care Timeline"] = data["Care Timeline"].apply(lambda x: str(x).replace("\n", "<br>"))
       data["Follow-Up Appointment"] = data["Follow-Up Appointment"].apply(lambda x: str(x).replace("\n", "<br>"))
       table_html = data.to_html(index=False, classes="styled-table", escape=False, justify="center")
       st.markdown(table_html, unsafe_allow_html=True)
   elif selected_module == "Date Relevant Details":
       st.markdown("<div class='custom-header'>Date Relevant Details</div>", unsafe_allow_html=True)
       table_html = data.to_html(index=False, classes="styled-table", escape=False, justify="center")
       st.markdown(table_html, unsafe_allow_html=True)
   elif selected_module == "Data":
       st.markdown("<div class='custom-header'>Patient 360 Data</div>", unsafe_allow_html=True)
       for index, row in data.iterrows():
           st.markdown(f"### Patient {index + 1}")
           cols = st.columns(2)
           for col_index, col_name in enumerate(data.columns):
               value = clean_text(row[col_name])
               with cols[col_index % 2]:
                   st.markdown(f"**{col_name}:** {value}")
   elif selected_module == "Discharge Summary":
       st.markdown("<div class='custom-header'>Discharge Summary</div>", unsafe_allow_html=True)
       data["Change Observed"] = data["Change Observed"].apply(lambda x: str(x).replace("\n", "<br>"))
       table_html = data.to_html(index=False, classes="styled-table", escape=False, justify="center")
       st.markdown(table_html, unsafe_allow_html=True)