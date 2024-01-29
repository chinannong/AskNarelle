import random
import time
from datetime import datetime
import pytz
import os
import requests
from dotenv import load_dotenv

import streamlit as st
from msal import ConfidentialClientApplication, PublicClientApplication

from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage

import webbrowser

import pyperclip

from Narelle import Narelle
from AN_Util import DBConnector
import LongText


def getTime():
    curr_time = {
                    "text" : datetime.now(st.session_state.tz).strftime("%Y-%m-%d %H:%M:%S"),
                    "timestamp": datetime.now(st.session_state.tz).timestamp()
                }
    return curr_time



################## MAIN ##############################
load_dotenv(override=True)

APP_REGISTRATION_CLIENT_ID = os.environ['APP_REG_CLIENT_ID']

st.set_page_config(page_title='AskNarelle - Your friendly course assistant', page_icon="🙋‍♀️")
st.title(":woman-raising-hand: Ask Narelle")
st.write("For queries related to SC1015/CE1115/CZ1115 - Introduction to Data Science & Artificial Intellegence")


st.session_state

if "user" not in st.session_state:
    st.session_state.informed_consent_height = 300
    # st.session_state.informed_consent = st.text_area("INFORMED CONSENT", label_visibility="collapsed" ,placeholder=LongText.TERMS_OF_USE, disabled=True, height=st.session_state.informed_consent_height)
    st.session_state.informed_consent = st.expander("Remote Informed Consent & Terms of Use".upper(), expanded=True)
    st.session_state.informed_consent.write(LongText.TERMS_OF_USE)
    # st.code(LongText.TERMS_OF_USE)

    st.session_state.agreebtn = st.checkbox(LongText.CONSENT_ACKNOWLEDGEMENT)
    cols = st.columns(4)
    with cols[0]:
        btn_agree = st.button("Agree and Start", disabled=not(st.session_state.agreebtn))
    with cols[1]:
        btn_copy = st.button("Copy Consent Form")

    if btn_copy:
        pyperclip.copy(f"{LongText.TERMS_OF_USE} \n\n ✔️ {LongText.CONSENT_ACKNOWLEDGEMENT}")
        msg = st.success("Text Copied...")
        time.sleep(2)
        msg.empty()

    st.toggle("ON OFF")

    if btn_agree:
        progress_bar = st.progress(0, text="Redirecting...")
        app = PublicClientApplication(
        client_id=APP_REGISTRATION_CLIENT_ID, 
        authority='https://login.microsoftonline.com/common'
        # token_cache=...  # Default cache is in memory only.
                        # You can learn how to use SerializableTokenCache from
                        # https://msal-python.readthedocs.io/en/latest/#msal.SerializableTokenCache
        )
        # Firstly, check the cache to see if this end user has signed in before
        result = None
        st.session_state.accounts = app.get_accounts()
        print(f"Account Exist: {st.session_state.accounts}")
        # if accounts:
        #     logging.info("Account(s) exists in cache, probably with token too. Let's try.")
        #     print("Account(s) already signed in:")
        #     for a in accounts:
        #         print(a["username"])
        #     chosen = accounts[0]  # Assuming the end user chose this one to proceed
        #     print("Proceed with account: %s" % chosen["username"])
        #     # Now let's try to find a token in cache for this account
        #     result = app.acquire_token_silent(["User.Read"], account=chosen)

        if not result:
            # logging.info("No suitable token exists in cache. Let's get a new one from AAD.")
            # print("A local browser window will be open for you to sign in. CTRL+C to cancel.")
            # result = app.acquire_token_interactive(scopes=["User.Read"])

            # Using Authentication Flow Instead:
            flow = app.initiate_device_flow(scopes=["User.Read"])

            # print(f"URL: {flow['verification_uri']}, Access Code: {flow['user_code']}")

            
            st.session_state.informed_consent.write(f"Authentication Process: \n1) Go to : {flow['verification_uri']}\n2) Enter Access Code: {flow['user_code']}\n 3) Verify Identity with NTU Email\n 4) Accept App Access Permission.")

            # st.write(f"Authentication Process: \n1) Go to : {flow['verification_uri']}\n2) Enter Access Code: {flow['user_code']}\n 3) Verify Identity with NTU Email\n 4) Accept App Access Permission.")
            
            result = app.acquire_token_by_device_flow(flow)


            st.session_state.accounts = app.get_accounts()
                
        
        progress_bar.progress(50, text="Authenticating...")
        if "access_token" in result:
            # Calling graph using the access token
            # graph_response = requests.get(  # Use token to call downstream service
            #     "https://graph.microsoft.com/v1.0/me",
            #     headers={'Authorization': 'Bearer ' + result['access_token']},)
            
            st.session_state.user = result['id_token_claims']['name']
            st.session_state.email = result['id_token_claims']['preferred_username']
            progress_bar.progress(50, text="Retriving profile")

            ## INITIALIZED CONVERSATIONS
            progress_bar.progress(80, text="Waking up Narelle...")
            DB_HOST = os.environ['CA_MONGO_DB_HOST']
            DB_USER = os.environ['CA_MONGO_DB_USER']
            DB_PASS = os.environ['CA_MONGO_DB_PASS']
            # st.session_state.chatlog = DBConnector(DB_HOST, DB_USER, DB_PASS).getDB("chatlog")
            st.session_state.chatlog = DBConnector(DB_HOST).getDB("chatlog")

            ## Initializing Conversations
            st.session_state.tz = pytz.timezone("Asia/Singapore")
            st.session_state.starttime = getTime()
            # init_time = {
            #                 "text" : st.session_state.starttime.strftime("%Y-%m-%d %H:%M:%S"),
            #                 "timestamp": st.session_state.starttime.timestamp()
            #             }
            conversation = {
                "stime" : getTime(),
                "user": st.session_state.user,
                "email": st.session_state.email,
                "messages":[],
                "last_interact": getTime() 
            }
            st.session_state.conv_id = st.session_state.chatlog.conversations.insert_one(conversation).inserted_id

            LLM_DEPLOYMENT_NAME = os.environ['AZURE_OPENAI_DEPLOYMENT_NAME']
            LLM_MODEL_NAME = os.environ['AZURE_OPENAI_MODEL_NAME']
            st.session_state.llm = Narelle(deployment_name=LLM_DEPLOYMENT_NAME, model_name=LLM_MODEL_NAME)
            st.session_state.conversation = []
            st.session_state.display_messages = [{"role":"ai", "content":f"{LongText.NARELLE_GREETINGS}", "recorded_on": getTime()}]

            progress_bar.progress(100, text="Narelle is Ready")
            time.sleep(2)
            progress_bar.empty()
            time.sleep(1)
            st.rerun()
        else:
            st.write(result.get("error"))
            st.write(result.get("error_description"))
            st.write(result.get("correlation_id"))  # You may need this when reporting a bug

else:

    ans = None
    for message in st.session_state.display_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if question:= st.chat_input("Type in your question here"):
        st.chat_message("user").markdown(question)
        if "quit" in question:
            print(f"Exiting Program: Conversation {len(st.session_state.conversation)}")
            for con in st.session_state.conversation:
                print(con)
        else:    
            u_message = {"role":"user", "content":question, "recorded_on": getTime()}
            st.session_state.display_messages.append(u_message)
            st.session_state.conversation.append(u_message)
            st.session_state.chatlog.conversations.update_one({"_id":st.session_state.conv_id}, {"$push":{"messages":u_message}, "$set":{"last_interact": getTime()}})
            
            
            answer, token_cost = st.session_state.llm.answer_this(query=question)
            with st.chat_message("assistant"):
                st.markdown(answer)
            
            ai_message = {"role":"ai", "content":f"{answer}", "recorded_on": getTime(), "token_cost":token_cost}
            st.session_state.display_messages.append(ai_message)
            st.session_state.conversation.append(ai_message)
            st.session_state.chatlog.conversations.update_one({"_id":st.session_state.conv_id}, {"$push":{"messages":ai_message}, "$set":{"last_interact": getTime(), "overall_cost":st.session_state.llm.get_total_tokens_cost()}})

    
    # st.write(st.session_state)
    # st.button("Test Refresh Button")
