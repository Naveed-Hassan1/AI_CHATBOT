from langchain_ollama import ChatOllama
from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_message_histories import SQLChatMessageHistory
from langchain_core.runnables import RunnableWithMessageHistory
import streamlit as st
import sqlite3

load_dotenv("./.env")

llm = ChatOllama(base_url="http://localhost:11434", model="qwen2.5:3b", temperature=0.5, max_tokens=500)
pt = ChatPromptTemplate.from_messages([("placeholder", "{history}"), ("human", "{prompt}")])
chain = pt | llm | StrOutputParser()

def history_finder(session_id):
    return SQLChatMessageHistory(session_id=session_id, connection="sqlite:///storage.db")

obj = RunnableWithMessageHistory(
    chain, 
    history_finder, 
    input_messages_key="prompt", 
    history_messages_key="history"
)

st.title(f"Hi,How can we help you?")


#Extracting all session as a Button 
try:
    conn = sqlite3.connect("./storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM message_store")
    rows = cursor.fetchall()
    conn.close()
    existing_sessions =  [row[0] for row in rows]
except sqlite3.OperationalError:
    existing_sessions =  []

#Logic to add buttons for session_id


with st.sidebar:
    st.image("./logo.png", width=200)
    if existing_sessions:
        selected = st.selectbox("Select session:",options=existing_sessions + ["+ Create new"])
        if selected == "+ Create new":
            session_id = st.text_input("Enter new session id:", value="NewSession")
        else:
            session_id = selected
    else:
        session_id = st.text_input("Enter session id :", value="Naveed")

if 'current_session' not in st.session_state or st.session_state.current_session != session_id:
    st.session_state.current_session = session_id
    st.session_state.storage = []
    
    past_messages = history_finder(session_id).messages
    for chat in past_messages:
        st.session_state.storage.append({"role": chat.type, "content": chat.content})

with st.sidebar:     
    if st.button("Remove session"):
        hist = history_finder(session_id)
        hist.clear()                     
        st.session_state.storage = []    
        st.rerun()                 



for msg in st.session_state.storage:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Enter text here ...")

if prompt:
    st.session_state.storage.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ========== STREAMING RESPONSE (changed lines) ==========
    with st.chat_message("assistant"):
        sample = st.empty()
        full_response = ""
        for chunk in obj.stream({"prompt": prompt}, config={"configurable": {"session_id": session_id}}):
            full_response += chunk
            sample.markdown(full_response)

    st.session_state.storage.append({"role": "assistant", "content": full_response})