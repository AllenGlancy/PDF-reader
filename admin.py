from langchain.vectorstores import Qdrant
from langchain.embeddings.openai import OpenAIEmbeddings
import qdrant_client
import os
import pytesseract
from langchain.text_splitter import CharacterTextSplitter
import streamlit as st
from dotenv import load_dotenv
import os
from PIL import Image
import io
import fitz
import hashlib
import mysql.connector
from datetime import datetime

#establishing connection to mysql database
def create_db_connection():
 return mysql.connector.connect(
    host= "localhost",    
    user= os.environ.get('SQL_USER'),   # MySQL username
    passwd=os.environ.get('SQL_PASS'), # MySQL password
    database="pdf_hash_database"
)

#generating MD5 hash
def md5_hash_text_chunks(text_chunks):
    md5_hash = hashlib.md5()
    for chunk in text_chunks:
        # Hash each chunk and update the overall hash
        chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
        md5_hash.update(chunk_hash.encode())
    return md5_hash.hexdigest()

#checking if the hash already exists in the database
def check_if_exists(hash_value):
    db = create_db_connection()
    cursor = db.cursor()
    query = "SELECT COUNT(*) FROM pdf_hash WHERE `pdf_hash` = %s"
    cursor.execute(query, (hash_value,))
    exists = cursor.fetchone()[0] > 0
    cursor.close()
    db.close()
    return exists

#inserting MD5 hash to SQL database
def save_to_database(file_name, hash_value):
    db = create_db_connection() 
    cursor = db.cursor()
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = "INSERT INTO pdf_hash (`Date`, `pdf_name`, `pdf_hash`) VALUES (%s, %s, %s)"
    values = (date_now, file_name, hash_value)
    try:
        cursor.execute(query, values)
        db.commit()
        result = True
    except mysql.connector.errors.IntegrityError:
        result = False
    finally:
        cursor.close()
        db.close()
    return result

# extracting text using ocr
def pdf_to_text_ocr(pdf_docs):
    text = ""
    pdf_docs.seek(0)
    # Read the stream into a bytes object
    pdf_bytes = pdf_docs.read()
    with fitz.open("pdf", pdf_bytes) as doc:
        for page_num in range(len(doc)):
            # Converting PDF page to image
            page = doc.load_page(page_num)
            pix = page.get_pixmap()
            image_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(image_bytes))

            # Using pytesseract to do OCR on the image
            page_text = pytesseract.image_to_string(image)
            text += page_text + "\n"
    return text

#splitting text into text chunks 
def get_text_chunks(extracted_text):
   text_splitter = CharacterTextSplitter(
    separator = "\n",
    chunk_size = 1000,
    chunk_overlap = 200,
    length_function = len,
)
   chunks = text_splitter.split_text(extracted_text)
   return chunks

#defining vector store 
def get_vectorstore(text_chunks,clear_existing=True):
   collection_name = os.getenv("Q_COLLECTION")
   print("Using collection:", collection_name)

   client = qdrant_client.QdrantClient(
        os.getenv("Q_HOST"),
        api_key=os.getenv("Q_API")
    )
   embeddings = OpenAIEmbeddings()
   if clear_existing:
    client.delete_collection(collection_name=collection_name)
    vectors_config = {
    "size": 1536,
    "distance": "Cosine" 
        }
   client.create_collection(collection_name=collection_name, vectors_config=vectors_config)
   vectorstore = Qdrant(
        client=client,
        collection_name=collection_name,
        embeddings=embeddings
    )

   vectorstore.add_texts(text_chunks)
   return vectorstore


def main():
    load_dotenv()
    st.set_page_config(page_title="St Lawrence College Policies", page_icon=":books:")
    st.header("Data Uploading Process")
    last_file_md5 = None
    pdf_docs = st.file_uploader("Upload your PDF files", type='pdf')
    if st.button("Upload"):
     with st.spinner("Processing"):
      if pdf_docs is not None:
        file_name = pdf_docs.name
        extracted_text = pdf_to_text_ocr(pdf_docs)
        text_chunks = get_text_chunks(extracted_text)
        hash_value = md5_hash_text_chunks(text_chunks)
        if check_if_exists(hash_value):
                st.warning("This file, or a file with similar content, has already been uploaded.")
        else:
                if save_to_database(file_name, hash_value):
                 vector_store = get_vectorstore(text_chunks, clear_existing=True)
                 st.success('File successfully uploaded')
                 


 
    
        
        

if __name__ == '__main__':
    main()
