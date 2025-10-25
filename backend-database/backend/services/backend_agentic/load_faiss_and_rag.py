import os
import sys
import logging
from typing import Dict, Any, List, Optional
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import CharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_deepseek import ChatDeepSeek
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

# Import agentic logging
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('faiss_rag')

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

def query_faiss_and_rag(query: str, user_id: str, lead_ids: Optional[List[str]] = None):
    """
    Builds and queries a FAISS RAG index.
    If lead_ids are provided, it filters the data to build a focused index on only those leads.
    """
    try:
        logger.info(f"FAISS RAG: Loading data for user_id: {user_id}. Focused on lead_ids: {lead_ids if lead_ids else 'All'}")
        
        try:
            from .main import get_user_drafts_data
        except ImportError:
            from main import get_user_drafts_data
        
        response = get_user_drafts_data()
        
        # --- Robust data extraction ---
        drafts_data = None
        if hasattr(response, 'get_json'):
            try:
                drafts_data = response.get_json()
            except Exception as json_error:
                logger.warning(f"Failed to parse JSON from Flask response: {json_error}")
        else:
            drafts_data = response
        
        if not drafts_data:
            return "No company data could be loaded for RAG."
        
        # --- NEW: Filter drafts_data if lead_ids are provided ---
        if lead_ids and isinstance(drafts_data, dict):
            filtered_drafts = {lid: data for lid, data in drafts_data.items() if lid in lead_ids}
            if not filtered_drafts:
                logger.warning(f"Provided lead_ids {lead_ids} not found in user's drafts. Falling back to all leads.")
            else:
                logger.info(f"Filtering RAG data to {len(filtered_drafts)} provided lead_ids.")
                drafts_data = filtered_drafts

        # Convert dict to list of (lead_id, data) tuples for processing
        if isinstance(drafts_data, dict):
            drafts = list(drafts_data.items())
        else:
            # This handles cases where data might be a list; assumes list of tuples/lists
            drafts = drafts_data

        if not drafts:
            return "No company data found for this user to build RAG index."

        # --- Document processing and vector store creation ---
        docs = []
        for lead_id, draft_data in drafts:
            if draft_data:
                company_name = (draft_data.get('company') or draft_data.get('Company Name') or '').strip()
                if company_name:
                    doc_parts = [f"Company: {company_name}", f"Lead ID: {lead_id}"]
                    for key, value in draft_data.items():
                        # Add all non-empty fields to the document for rich context
                        if value is not None and str(value).strip():
                            doc_parts.append(f"{key.replace('_', ' ').title()}: {value}")
                    docs.append(" | ".join(doc_parts))
        
        if not docs:
            return "No processable documents could be created from user data."

        text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=200, separator=" | ")
        doc_chunks = []
        for doc in docs:
            doc_chunks.extend(text_splitter.split_text(doc))

        if not doc_chunks:
            logger.warning("No document chunks were created after splitting.")
            return "No content available for semantic search."

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_texts(doc_chunks, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 8})

        llm = ChatDeepSeek(model="deepseek-chat", api_key=api_key, temperature=0.1)

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", retriever=retriever,
            return_source_documents=True, chain_type_kwargs={"prompt": _get_company_qa_prompt()}
        )
        
        result = qa_chain({"query": query})
        answer = result["result"]
        
        logger.info("RAG query completed successfully.")
        return answer
        
    except Exception as e:
        logger.error(f"Error in FAISS RAG query: {e}", exc_info=True)
        return f"Error processing query on your company data: {e}"

def _get_company_qa_prompt():
    """Get enhanced prompt template for company information queries"""
    from langchain.prompts import PromptTemplate
    
    template = """You are an expert business analyst with access to detailed company information from scraped lead data. 
    Use the following pieces of context to answer the question about companies. 
    
    Focus on providing specific, accurate information from the provided context. If asked about executives, leadership, 
    CEO, founders, or team members, look for fields like 'CEO', 'Founder', 'Leadership', 'Management', 'Team', etc.
    
    If you cannot find the specific information requested, clearly state what information is available instead.
    
    Context: {context}
    
    Question: {question}
    
    Detailed Answer:"""
    
    return PromptTemplate(template=template, input_variables=["context", "question"])

