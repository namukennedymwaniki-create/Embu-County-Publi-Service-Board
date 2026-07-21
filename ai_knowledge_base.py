# ai_knowledge_base.py
import streamlit as st
import google.generativeai as genai
import PyPDF2
import uuid
import io
import json
from datetime import datetime
from typing import List, Dict
import psycopg2

try:
    from pgvector.psycopg2 import register_vector
except ImportError:
    print("⚠️ pgvector not available")

class AIKnowledgeBase:
    def __init__(self):
        # Get API key from secrets
        self.api_key = st.secrets.get("GEMINI_API_KEY")
        if not self.api_key:
            st.error("❌ GEMINI_API_KEY not found in secrets. Please add it.")
            return
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Model settings - UPDATED with correct model names
        self.embedding_model = "models/text-embedding-004"  # ✅ FIXED
        self.chat_model = "gemini-1.5-flash"  # or "gemini-1.5-pro"
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        print(f"✅ AI Knowledge Base initialized with Gemini")
        print(f"📊 Using embedding model: {self.embedding_model}")
        print(f"💬 Using chat model: {self.chat_model}")
    
    def get_conn(self):
        """Get database connection with pgvector support"""
        database_url = st.secrets.get("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url, sslmode='require')
            try:
                register_vector(conn)
            except:
                pass
            return conn
        return None
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            st.error(f"Error extracting text: {e}")
            return ""
    
    def chunk_text(self, text: str) -> List[Dict]:
        """Split text into overlapping chunks"""
        chunks = []
        words = text.split()
        total_words = len(words)
        
        if total_words == 0:
            return chunks
        
        for i in range(0, total_words, self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            chunks.append({
                'chunk_number': len(chunks) + 1,
                'chunk_text': chunk_text
            })
            
            if i + self.chunk_size >= total_words:
                break
        
        return chunks
    
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding using Gemini"""
        try:
            # Gemini embedding model - UPDATED
            result = genai.embed_content(
                model=self.embedding_model,
                content=text[:8191],  # Gemini limit
                task_type="retrieval_document"
            )
            return result['embedding']
        except Exception as e:
            st.error(f"Error creating embedding: {e}")
            return []
    
    def process_document(self, file_content: bytes, filename: str, title: str, 
                         category: str, uploaded_by: str) -> Dict:
        """Process and store a document"""
        try:
            # Extract text
            text = self.extract_text_from_pdf(file_content)
            if not text.strip():
                return {'success': False, 'error': 'No text extracted from PDF'}
            
            # Create document record
            doc_id = str(uuid.uuid4())
            conn = self.get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO documents (
                    id, filename, title, category, uploaded_by, 
                    file_size, page_count, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                doc_id, filename, title, category, uploaded_by,
                len(file_content), text.count('\n') // 40 + 1, True
            ))
            
            # Chunk and embed
            chunks = self.chunk_text(text)
            chunk_count = 0
            
            for chunk in chunks:
                embedding = self.create_embedding(chunk['chunk_text'])
                if embedding:
                    chunk_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO document_chunks (
                            id, document_id, chunk_number, chunk_text, embedding
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        chunk_id, doc_id, chunk['chunk_number'],
                        chunk['chunk_text'], embedding
                    ))
                    chunk_count += 1
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'document_id': doc_id,
                'chunks_created': chunk_count,
                'message': f'Document processed with {chunk_count} chunks'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def search_documents(self, question: str, limit: int = 5) -> List[Dict]:
        """Search for relevant document chunks using Gemini embeddings"""
        try:
            # Create embedding for question
            question_embedding = self.create_embedding(question)
            if not question_embedding:
                return []
            
            conn = self.get_conn()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    dc.chunk_text,
                    dc.page_number,
                    d.title as document_title,
                    d.filename,
                    1 - (dc.embedding <=> %s::vector) as similarity
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.is_active = TRUE
                ORDER BY dc.embedding <=> %s::vector
                LIMIT %s
            """, (question_embedding, question_embedding, limit))
            
            results = cursor.fetchall()
            conn.close()
            
            return [{
                'chunk_text': r[0],
                'page_number': r[1],
                'document_title': r[2],
                'filename': r[3],
                'similarity': r[4]
            } for r in results]
            
        except Exception as e:
            st.error(f"Search error: {e}")
            return []
    
    def generate_answer(self, question: str, chunks: List[Dict]) -> Dict:
        """Generate answer using Gemini"""
        try:
            if not chunks:
                return {
                    'answer': "I couldn't find information related to your question in the uploaded knowledge base.",
                    'sources': []
                }
            
            # Prepare context
            context = "\n\n".join([
                f"From document '{chunk['document_title']}' (page {chunk['page_number']}):\n{chunk['chunk_text']}"
                for chunk in chunks[:3]
            ])
            
            prompt = f"""
            You are an AI assistant for Embu County Public Service Board. 
            Answer the following question based ONLY on the provided context.
            If the answer cannot be found in the context, say "I couldn't find information related to your question in the uploaded knowledge base."
            Do not use any external knowledge or make assumptions.
            
            Question: {question}
            
            Context:
            {context}
            
            Answer:"""
            
            # Generate with Gemini
            model = genai.GenerativeModel(self.chat_model)
            response = model.generate_content(prompt)
            
            answer = response.text
            
            # Extract sources
            sources = [
                {
                    'title': chunk['document_title'],
                    'page': chunk['page_number'],
                    'filename': chunk['filename']
                }
                for chunk in chunks[:3]
            ]
            
            return {
                'answer': answer,
                'sources': sources
            }
            
        except Exception as e:
            return {
                'answer': f"Error generating answer: {str(e)}",
                'sources': []
            }
