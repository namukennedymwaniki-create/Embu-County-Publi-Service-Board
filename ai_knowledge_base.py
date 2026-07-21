def ai_knowledge_base():
    """AI Knowledge Base module - Admin uploads, Users ask questions"""
    
    st.markdown("""
    <div class="main-header">
        <h1 style="color: white; margin: 0;">🤖 AI Knowledge Base</h1>
        <p style="color: rgba(255,255,255,0.8); margin-top: 0.5rem;">Ask questions about Embu County documents and policies</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Test Gemini connection
    try:
        from ai_knowledge_base import test_gemini_connection
        success, message = test_gemini_connection()
        if success:
            st.success(message)
        else:
            st.error(message)
            return
    except ImportError:
        st.error("❌ ai_knowledge_base.py not found. Please ensure the file exists.")
        return
    except Exception as e:
        st.error(f"❌ Error testing Gemini: {str(e)}")
        return
    
    # Initialize AI assistant
    try:
        from ai_knowledge_base import AIKnowledgeBase
        ai = AIKnowledgeBase()
    except ImportError as e:
        st.error(f"❌ AI Knowledge Base module not installed.")
        st.info("Run: pip install google-generativeai PyPDF2 pgvector")
        st.code(str(e))
        return
    except Exception as e:
        st.error(f"❌ Error initializing AI: {str(e)}")
        return
    
    # Check if user is admin
    is_admin = st.session_state.user.get("role") in ["Admin", "Super Admin"]
    
    # Create tabs
    if is_admin:
        tab1, tab2, tab3 = st.tabs(["💬 Ask AI", "📚 Knowledge Base", "📤 Upload Documents"])
    else:
        tab1, tab2 = st.tabs(["💬 Ask AI", "📚 Knowledge Base"])
    
    # ==================== TAB 1: ASK AI ====================
    with tab1:
        st.subheader("💬 Ask Questions")
        st.caption("Ask questions about uploaded documents and policies")
        
        # Chat interface
        if 'ai_chat_messages' not in st.session_state:
            st.session_state.ai_chat_messages = []
        
        # Display chat history
        for msg in st.session_state.ai_chat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if "sources" in msg and msg["sources"]:
                    with st.expander("📚 Sources"):
                        for source in msg["sources"]:
                            st.write(f"• **{source['title']}** - Page {source['page']}")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.ai_chat_messages = []
            st.rerun()
    
    # ==================== TAB 2: KNOWLEDGE BASE ====================
    with tab2:
        st.subheader("📚 Knowledge Base")
        st.caption("Browse all uploaded documents")
        
        # Filter
        col1, col2 = st.columns([2, 1])
        with col1:
            category_filter = st.selectbox(
                "Filter by Category",
                ["All Categories", "HR Policies", "Board Minutes", "Circulars", 
                 "Acts & Regulations", "Court Decisions", "Schemes of Service", 
                 "Reports", "Other"]
            )
        with col2:
            search_doc = st.text_input("Search Documents", placeholder="Search...")
        
        # Load documents from database
        try:
            conn = ai.get_conn()
            if conn:
                cursor = conn.cursor()
                is_cloud = st.secrets.get("DATABASE_URL") is not None
                
                query = "SELECT * FROM documents WHERE is_active = TRUE"
                params = []
                
                if category_filter != "All Categories":
                    if is_cloud:
                        query += " AND category = %s"
                    else:
                        query += " AND category = ?"
                    params.append(category_filter)
                
                if search_doc:
                    if is_cloud:
                        query += " AND (title ILIKE %s OR filename ILIKE %s)"
                    else:
                        query += " AND (title LIKE ? OR filename LIKE ?)"
                    search_pattern = f"%{search_doc}%"
                    params.extend([search_pattern, search_pattern])
                
                query += " ORDER BY upload_date DESC"
                
                if params:
                    cursor.execute(query, tuple(params))
                else:
                    cursor.execute(query)
                
                docs = cursor.fetchall()
                conn.close()
                
                if docs:
                    st.success(f"📊 Found {len(docs)} document(s)")
                    for doc in docs:
                        with st.expander(f"📄 {doc[2]} - {doc[3]}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Filename:** {doc[1]}")
                                st.write(f"**Category:** {doc[3]}")
                                st.write(f"**Uploaded:** {doc[5]}")
                            with col2:
                                st.write(f"**Pages:** {doc[7]}")
                                st.write(f"**Uploaded By:** {doc[6]}")
                            if doc[4]:
                                st.write(f"**Summary:** {doc[4]}")
                            
                            # Delete button for admin
                            if is_admin:
                                if st.button(f"🗑️ Delete", key=f"delete_doc_{doc[0]}"):
                                    conn2 = ai.get_conn()
                                    cursor2 = conn2.cursor()
                                    if is_cloud:
                                        cursor2.execute("DELETE FROM documents WHERE id = %s", (doc[0],))
                                    else:
                                        cursor2.execute("DELETE FROM documents WHERE id = ?", (doc[0],))
                                    conn2.commit()
                                    conn2.close()
                                    st.success(f"Document '{doc[2]}' deleted!")
                                    st.rerun()
                else:
                    st.info("📭 No documents uploaded yet. Upload your first document in the 'Upload Documents' tab.")
        except Exception as e:
            st.info("📚 Knowledge Base is ready for documents. Upload your first document!")
    
    # ==================== TAB 3: UPLOAD DOCUMENTS (Admin Only) ====================
    if is_admin:
        with tab3:
            st.subheader("📤 Upload Documents")
            st.caption("Upload documents to the AI knowledge base")
            
            st.info("""
            📌 **Upload Guidelines:**
            - Only PDF files are supported
            - Files should be text-based (not scanned images)
            - Max file size: 50MB
            - Documents will be processed and made searchable
            """)
            
            with st.form("upload_document_form"):
                uploaded_file = st.file_uploader(
                    "Choose a PDF document",
                    type=["pdf"],
                    help="Only PDF files are supported"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    title = st.text_input("Document Title *", placeholder="Enter a descriptive title")
                    category = st.selectbox(
                        "Category *",
                        ["HR Policies", "Board Minutes", "Circulars", 
                         "Acts & Regulations", "Court Decisions", 
                         "Schemes of Service", "Reports", "Other"]
                    )
                with col2:
                    summary = st.text_area("Summary (optional)", placeholder="Brief description of the document", height=100)
                
                submitted = st.form_submit_button("📤 Upload Document", type="primary", use_container_width=True)
                
                if submitted and uploaded_file and title:
                    with st.spinner("Processing document..."):
                        try:
                            # Show file info
                            file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # MB
                            st.info(f"📄 File: {uploaded_file.name} ({file_size:.2f} MB)")
                            
                            result = ai.process_document(
                                uploaded_file.getvalue(),
                                uploaded_file.name,
                                title,
                                category,
                                st.session_state.user.get("username", "admin")
                            )
                            
                            if result['success']:
                                st.success(f"✅ Document '{title}' uploaded successfully!")
                                st.info(f"📊 Created {result['chunks_created']} searchable chunks")
                                st.balloons()
                            else:
                                st.error(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                elif submitted:
                    if not uploaded_file:
                        st.warning("⚠️ Please select a PDF file")
                    if not title:
                        st.warning("⚠️ Please enter a document title")
            
            # Show existing documents in a compact view
            st.markdown("---")
            st.subheader("📋 Recently Uploaded Documents")
            try:
                conn = ai.get_conn()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT title, category, upload_date, filename, id 
                        FROM documents 
                        WHERE is_active = TRUE 
                        ORDER BY upload_date DESC 
                        LIMIT 5
                    """)
                    recent_docs = cursor.fetchall()
                    conn.close()
                    
                    if recent_docs:
                        for doc in recent_docs:
                            st.write(f"• **{doc[0]}** ({doc[1]}) - {doc[2]}")
                    else:
                        st.caption("No documents uploaded yet")
            except:
                pass
    
    # =========================================================
    # CHAT INPUT - PLACED OUTSIDE ALL CONTAINERS
    # =========================================================
    if question := st.chat_input("Ask your question here..."):
        # Add user message
        st.session_state.ai_chat_messages.append({
            "role": "user",
            "content": question
        })
        
        # Get AI response
        with st.spinner("🔍 Searching knowledge base..."):
            try:
                # Search for relevant documents
                chunks = ai.search_documents(question)
                
                # Generate answer
                result = ai.generate_answer(question, chunks)
                
                # Add assistant response
                st.session_state.ai_chat_messages.append({
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"]
                })
                
                # Rerun to update the chat display
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                # Add error message to chat
                st.session_state.ai_chat_messages.append({
                    "role": "assistant",
                    "content": f"❌ An error occurred: {str(e)}",
                    "sources": []
                })
                st.rerun()
