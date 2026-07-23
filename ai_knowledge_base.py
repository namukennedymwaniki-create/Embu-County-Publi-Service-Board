# ai_knowledge_base.py
import streamlit as st
import google.generativeai as genai
import PyPDF2
import uuid
import io
import re
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
        
        # Find working chat model
        chat_models_to_try = [
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-pro",
            "gemini-1.0-pro",
        ]
        
        self.chat_model = None
        for model_name in chat_models_to_try:
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
            st.error("❌ No working chat model found. Please check your API key.")
            return
        
        # Embedding models
        self.embedding_models = [
            "text-embedding-004",
            "text-embedding-003",
            "embedding-001",
        ]
        
        # Initialize feedback storage
        self.feedback_data = []
        
        self.chunk_size = 500  # Smaller chunks for better accuracy
        self.chunk_overlap = 100
        
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
        """Extract text from PDF with page tracking"""
        text = ""
        page_markers = []
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page_num, page in enumerate(pdf_reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    # Track where each page starts
                    page_markers.append({
                        'page': page_num,
                        'start_index': len(text)
                    })
                    text += page_text + "\n"
                else:
                    st.warning(f"⚠️ No text extracted from page {page_num}")
            return text, page_markers
        except Exception as e:
            st.error(f"Error extracting text: {e}")
            return "", []
    
    def chunk_text(self, text: str, page_markers: List[Dict] = None) -> List[Dict]:
        """Split text into overlapping chunks with page info"""
        chunks = []
        words = text.split()
        total_words = len(words)
        
        if total_words == 0:
            return chunks
        
        for i in range(0, total_words, self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            
            # Determine page number for this chunk
            page_num = 1
            if page_markers:
                # Estimate character position
                char_pos = len(" ".join(words[:i]))
                for marker in page_markers:
                    if marker['start_index'] <= char_pos:
                        page_num = marker['page']
            
            chunks.append({
                'chunk_number': len(chunks) + 1,
                'chunk_text': chunk_text,
                'page_number': page_num
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
    
    def generate_document_summary(self, text: str) -> str:
        """Generate a summary of the document"""
        try:
            # Take first 5000 characters for summary
            sample_text = text[:5000]
            
            prompt = f"""
            Please provide a brief summary of this document in 2-3 sentences:
            
            {sample_text}
            
            Summary:"""
            
            model = genai.GenerativeModel(self.chat_model)
            response = model.generate_content(prompt)
            return response.text if response and response.text else "Summary not available"
        except:
            return "Summary not available"
    
    def process_document(self, file_content: bytes, filename: str, title: str, 
                         category: str, uploaded_by: str) -> Dict:
        """Process and store a document with debugging"""
        try:
            st.info("📄 Extracting text from PDF...")
            text, page_markers = self.extract_text_from_pdf(file_content)
            if not text.strip():
                return {'success': False, 'error': 'No text extracted from PDF'}
            
            st.info(f"📊 Extracted {len(text)} characters of text")
            
            # Generate summary
            st.info("📝 Generating document summary...")
            summary = self.generate_document_summary(text)
            st.info(f"📋 Summary: {summary[:100]}...")
            
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
                    file_size, page_count, summary, is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                doc_id, filename, title, category, uploaded_by,
                len(file_content), len(page_markers) if page_markers else 1,
                summary, True
            ))
            
            # Chunk and embed
            st.info("✂️ Splitting text into chunks...")
            chunks = self.chunk_text(text, page_markers)
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
                            id, document_id, chunk_number, chunk_text, embedding, page_number
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        chunk_id, doc_id, chunk['chunk_number'],
                        chunk['chunk_text'], embedding, chunk['page_number']
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
                'summary': summary,
                'message': f'Document processed with {chunk_count}/{len(chunks)} chunks'
            }
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def calculate_confidence(self, chunks: List[Dict]) -> float:
        """Calculate confidence score based on similarity scores"""
        if not chunks:
            return 0.0
        
        # Average similarity of top chunks
        similarities = [chunk.get('similarity', 0) for chunk in chunks[:3]]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        
        # Confidence is based on similarity threshold
        if avg_similarity > 0.75:
            return 0.9  # High confidence
        elif avg_similarity > 0.6:
            return 0.7  # Medium confidence
        elif avg_similarity > 0.4:
            return 0.5  # Low confidence
        else:
            return 0.3  # Very low confidence
    
    def search_documents(self, question: str, limit: int = 5) -> List[Dict]:
        """Enhanced search with query expansion"""
        try:
            # Create embedding for question
            question_embedding = self.create_embedding(question)
            if not question_embedding:
                return []
            
            # Expand query with key terms
            keywords = re.findall(r'\b[A-Za-z]{3,}\b', question)
            keywords_str = " ".join(keywords[:10])
            
            conn = self.get_conn()
            if not conn:
                return []
            
            cursor = conn.cursor()
            
            # Combined search: vector similarity + keyword matching
            cursor.execute("""
                SELECT 
                    dc.chunk_text,
                    dc.page_number,
                    d.title as document_title,
                    d.filename,
                    1 - (dc.embedding <=> %s::vector) as similarity,
                    CASE 
                        WHEN d.title ILIKE %s THEN 0.2
                        ELSE 0
                    END as title_boost
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.is_active = TRUE
                ORDER BY (1 - (dc.embedding <=> %s::vector) + 
                          CASE WHEN d.title ILIKE %s THEN 0.2 ELSE 0 END) DESC
                LIMIT %s
            """, (question_embedding, f'%{question}%', question_embedding, f'%{question}%', limit))
            
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
        """Generate answer with follow-up questions and confidence"""
        try:
            if not chunks:
                return {
                    'answer': "I couldn't find information related to your question in the uploaded knowledge base.",
                    'sources': [],
                    'follow_up': [],
                    'confidence': 0.0
                }
            
            # Calculate confidence
            confidence = self.calculate_confidence(chunks)
            
            # Prepare context with sources
            context = "\n\n".join([
                f"[Document: {chunk['document_title']}, Page: {chunk['page_number']}]\n{chunk['chunk_text']}"
                for chunk in chunks[:3]
            ])
            
            prompt = f"""
            You are an AI assistant for the Embu County Public Service Board HR System.
            
            **Role**: You provide accurate, helpful information about HR policies, procedures, and regulations.
            
            **Instructions**:
            1. Answer ONLY based on the provided context
            2. If the information is not in the context, say so clearly
            3. Be specific and cite the document and page number
            4. Use bullet points for clarity when listing items
            5. If the question is unclear, ask for clarification
            6. Provide practical, actionable information
            7. After your answer, suggest 2-3 relevant follow-up questions
            
            **Context**:
            {context}
            
            **Question**: {question}
            
            **Answer with follow-up questions**:"""
            
            model = genai.GenerativeModel(self.chat_model)
            response = model.generate_content(prompt)
            
            response_text = response.text if response and response.text else "No response generated."
            
            # Parse follow-up questions
            follow_up = []
            if "Follow-up" in response_text or "follow-up" in response_text:
                parts = response_text.split("Follow-up" if "Follow-up" in response_text else "follow-up")
                answer_text = parts[0].strip()
                if len(parts) > 1:
                    follow_up_matches = re.findall(r'\d+\.\s*(.+?)(?=\d+\.|$)', parts[1])
                    follow_up = [q.strip() for q in follow_up_matches[:3]]
                else:
                    answer_text = response_text
                    follow_up = []
            else:
                answer_text = response_text
                follow_up = []
            
            return {
                'answer': answer_text,
                'sources': [{
                    'title': chunk['document_title'],
                    'page': chunk['page_number'],
                    'filename': chunk['filename']
                } for chunk in chunks[:3]],
                'follow_up': follow_up,
                'confidence': confidence
            }
        except Exception as e:
            return {
                'answer': f"Error: {str(e)}",
                'sources': [],
                'follow_up': [],
                'confidence': 0.0
            }
