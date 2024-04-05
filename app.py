import streamlit as st
from dotenv import load_dotenv
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.llms import OpenAI
from langchain.chains import RetrievalQA
import qdrant_client
from langchain.vectorstores import Qdrant
import os

def get_embeddings():
    client = qdrant_client.QdrantClient(
        os.getenv("Q_HOST"),
        api_key=os.getenv("Q_API")
    )
    embeddings = OpenAIEmbeddings()
    vectorstore = Qdrant(
        client=client,
        collection_name=os.getenv("Q_COLLECTION"),
        embeddings=embeddings
    )

    return vectorstore


def main():
    load_dotenv()
    st.set_page_config(page_title="St Lawrence College Policies", page_icon=":books:")
    col1, col2, col3 = st.columns([2,6,3])
    with col3:
     st.image('college logo.png')
    st.header("College Policies")
    #Embeddings
    vectorstore = get_embeddings()
    #qa_chain
    qa = RetrievalQA.from_chain_type(
      llm=OpenAI(),
      chain_type="stuff",
      retriever=vectorstore.as_retriever()
     )

    #user input
    user_question = st.text_input("Ask your question about the policies")
    if user_question:
        st.write(f"Question: {user_question}")
        answer = qa.run(user_question)
        st.write(f"Answer: {answer}")
    




if __name__ =='__main__':
    main()

