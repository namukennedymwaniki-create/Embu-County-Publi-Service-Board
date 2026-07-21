import google.generativeai as genai

class AIKnowledgeBase:
    def __init__(self):
        self.api_key = st.secrets.get("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        
    def create_embedding(self, text: str) -> List[float]:
        """Create embedding using Gemini"""
        try:
            model = genai.embedding_models.EmbeddingModel("models/embedding-001")
            result = model.embed_content(text)
            return result.embedding
        except Exception as e:
            st.error(f"Error creating embedding: {e}")
            return []
    
    def generate_answer(self, question: str, chunks: List[Dict]) -> Dict:
        """Generate answer using Gemini"""
        try:
            if not chunks:
                return {
                    'answer': "I couldn't find information related to your question.",
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
            
            Question: {question}
            
            Context:
            {context}
            
            Answer:"""
            
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            
            return {
                'answer': response.text,
                'sources': chunks[:3]
            }
        except Exception as e:
            return {
                'answer': f"Error: {str(e)}",
                'sources': []
            }
