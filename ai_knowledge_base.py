# ai_knowledge_base.py
import streamlit as st
import google.generativeai as genai
import PyPDF2
import uuid
import io
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
        
        # =========================================================
        # CHAT MODELS - Try these in order
        # =========================================================
        self.chat_models_to_try = [
            "models/gemini-2.5-flash",      # ✅ Available
            "models/gemini-2.0-flash",       # ✅ Available
            "models/gemini-flash-latest",    # ✅ Available
            "models/gemini-2.5-pro",         # ✅ Available
            "models/gemini-pro-latest",      # ✅ Available
        ]
        
        # Find working chat model
        self.chat_model = None
        for model_name in self.chat_models_to_try:
            try:
                test_model = genai.GenerativeModel(model_name)
                response = test_model.generate_content("Test")
                if response and response.text:
                    self.chat_model = model_name
                    print(f"✅ Using chat model: {model_name}")
                    break
            except Exception as e:
                print(f"❌ {model_name} failed: {e}")
                continue
        
        if not self.chat_model:
            # Try to list available models for debugging
            try:
                print("Available models:")
                for m in genai.list_models():
                    print(f"  - {m.name}")
            except:
                pass
            st.error("❌ No working chat model found. Please check your API key.")
            return
        
        # =========================================================
        # EMBEDDING MODELS
        # =========================================================
        self.embedding_models = [
            "models/gemini-embedding-2",         # ✅ Available
            "models/gemini-embedding-2-preview", # ✅ Available
            "models/gemini-embedding-001",       # ✅ Available
        ]
        
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        print(f"✅ AI Knowledge Base initialized successfully")
        print(f"📊 Chat model: {self.chat_model}")
    
    def get_conn(self):
        """Get database connection with pgvector support"""
        database_url = st.secrets.get("DATABASE_URL")
        if database_url:
            try:
                conn = psycopg2.connect(database_url, sslmode='require')
                try:
                    register_vector(conn)
                except:
                    pass
                return conn
            except Exception as e:
                st.error(f"Database connection error: {e}")
                return None
        return None
    
    def extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF"""
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
                else:
                    st.warning(f"⚠️ No text extracted from page {page_num}")
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
        """Create embedding using Gemini with fallback models"""
        for model_name in self.embedding_models:
            try:
                result = genai.embed_content(
                    model=model_name,
                    content=text[:8191],
                    task_type="retrieval_document"
                )
                print(f"✅ Embedding successful with {model_name}")
                return result['embedding']
            except Exception as e:
                print(f"❌ {model_name} failed: {e}")
                continue
        
        st.error("❌ All embedding models failed")
        return []
    
    def process_document(self, file_content: bytes, filename: str, title: str, 
                         category: str, uploaded_by: str) -> Dict:
        """Process and store a document"""
        try:
            st.info("📄 Extracting text from PDF...")
            text = self.extract_text_from_pdf(file_content)
            if not text.strip():
                return {'success': False, 'error': 'No text extracted from PDF'}
            
            st.info(f"📊 Extracted {len(text)} characters of text")
            
            # Create document record
            doc_id = str(uuid.uuid4())
            conn = self.get_conn()
            if not conn:
                return {'success': False, 'error': 'Database connection failed'}
            
            cursor = conn.cursor()
            
            st.info("💾 Saving document record...")
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
            st.info("✂️ Splitting text into chunks...")
            chunks = self.chunk_text(text)
            st.info(f"📋 Created {len(chunks)} chunks")
            
            if not chunks:
                return {'success': False, 'error': 'No chunks created from text'}
            
            chunk_count = 0
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, chunk in enumerate(chunks):
                status_text.text(f"Processing chunk {i+1}/{len(chunks)}...")
                
                if i == 0:
                    st.info(f"📝 First chunk preview: {chunk['chunk_text'][:200]}...")
                
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
                else:
                    st.warning(f"⚠️ Failed to create embedding for chunk {i+1}")
                
                progress_bar.progress((i + 1) / len(chunks))
            
            conn.commit()
            conn.close()
            status_text.empty()
            progress_bar.empty()
            
            if chunk_count == 0:
                return {
                    'success': False,
                    'error': f'No embeddings created. Failed to process all {len(chunks)} chunks'
                }
            
            return {
                'success': True,
                'document_id': doc_id,
                'chunks_created': chunk_count,
                'total_chunks': len(chunks),
                'message': f'Document processed with {chunk_count}/{len(chunks)} chunks'
            }
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def search_documents(self, question: str, limit: int = 5) -> List[Dict]:
        """Search for relevant document chunks"""
        try:
            question_embedding = self.create_embedding(question)
            if not question_embedding:
                return []
            
            conn = self.get_conn()
            if not conn:
                return []
            
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
            
            if not results:
                return []
            
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
            
            model = genai.GenerativeModel(self.chat_model)
            response = model.generate_content(prompt)
            
            answer = response.text
            
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
