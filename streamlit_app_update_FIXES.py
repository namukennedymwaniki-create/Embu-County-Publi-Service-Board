# =========================================================
# FIXES FOR TAB 3 AND TAB 4
# =========================================================

# FIX 1: In the TAB 3 section, when displaying shortlisted candidates
# Replace the dataframe display section with this to handle decimal ID numbers:

# ==================== TAB 3: SHORTLISTED CANDIDATES ====================
with tab3:
    st.subheader("📊 Shortlisted Candidates")
    
    conn = get_conn()
    if conn is None:
        st.error("Cannot connect to database")
        return
    
    is_cloud = st.secrets.get("DATABASE_URL") is not None
    
    # Get open advertised positions for filtering
    open_positions_df = pd.read_sql("SELECT position_title FROM advertised_positions WHERE status = 'Open'", conn)
    open_positions_list = open_positions_df['position_title'].tolist() if not open_positions_df.empty else []
    
    # Search bar for shortlisted candidates - COMPACT LAYOUT
    st.markdown("### 🔍 Search & Filter")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        search_shortlist = st.text_input("Search Name/ID", placeholder="Type name or ID...", key="search_shortlist")
    
    with col2:
        # Only show open positions in filter
        position_list = ["All"] + sorted(open_positions_list) if open_positions_list else ["All"]
        position_filter = st.selectbox("Position", position_list, key="pos_filter")
    
    with col3:
        subcounty_query = "SELECT DISTINCT subcounty FROM staff WHERE application_status = 'Shortlisted'"
        subcounty_df = pd.read_sql(subcounty_query, conn)
        subcounty_list = ["All"] + sorted(subcounty_df['subcounty'].dropna().unique().tolist())
        subcounty_filter_shortlist = st.selectbox("Sub-County", subcounty_list, key="sub_filter")
    
    with col4:
        ward_query = "SELECT DISTINCT ward FROM staff WHERE application_status = 'Shortlisted'"
        ward_df = pd.read_sql(ward_query, conn)
        ward_list = ["All"] + sorted(ward_df['ward'].dropna().unique().tolist())
        ward_filter = st.selectbox("Ward", ward_list, key="ward_filter")
    
    with col5:
        gender_list = ["All", "Male", "Female"]
        gender_filter = st.selectbox("Gender", gender_list, key="gender_filter")
    
    # Age filter in a separate row
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        age_query = "SELECT yob FROM staff WHERE application_status = 'Shortlisted'"
        age_df = pd.read_sql(age_query, conn)
        if not age_df.empty and not age_df['yob'].isna().all():
            current_year = datetime.now().year
            age_df['age'] = current_year - age_df['yob']
            min_age = int(age_df['age'].min()) if not age_df['age'].isna().all() else 18
            max_age = int(age_df['age'].max()) if not age_df['age'].isna().all() else 100
            age_range = st.slider("Age Range", min_age, max_age, (min_age, max_age), key="age_slider")
        else:
            age_range = (18, 100)
            st.slider("Age Range", 18, 100, (18, 100), key="age_slider")
    
    # Compact refresh buttons
    col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
    with col2:
        if st.button("🔄 Refresh", use_container_width=True, key="refresh_shortlist"):
            st.cache_data.clear()
            st.rerun()
    with col3:
        if st.button("📊 Show All", use_container_width=True, key="show_all_shortlist"):
            st.rerun()
    with col4:
        if st.button("🗑️ Clear Filters", use_container_width=True, key="clear_filters"):
            st.rerun()
    
    st.markdown("---")
    
    try:
        # Build query with filters - ONLY OPEN POSITIONS
        query = """
            SELECT id, name, id_number, contact, email, qualifications, experience_years, 
                   application_status, subcounty, position_applied, shortlist_date, 
                   gender, yob, ward
            FROM staff 
            WHERE application_status = 'Shortlisted'
        """
        
        # Only show candidates for open positions
        if open_positions_list:
            if is_cloud:
                placeholders = ','.join(['%s'] * len(open_positions_list))
                query += f" AND position_applied IN ({placeholders})"
                params = open_positions_list.copy()
            else:
                placeholders = ','.join(['?'] * len(open_positions_list))
                query += f" AND position_applied IN ({placeholders})"
                params = open_positions_list.copy()
        else:
            # No open positions, show nothing
            params = []
            query += " AND 1=0"
        
        if search_shortlist:
            if is_cloud:
                query += " AND (name ILIKE %s OR id_number::TEXT ILIKE %s)"
            else:
                query += " AND (name LIKE ? OR id_number LIKE ?)"
            search_pattern = f"%{search_shortlist}%"
            params.extend([search_pattern, search_pattern])
        
        if position_filter != "All" and position_filter in open_positions_list:
            if is_cloud:
                query += " AND position_applied = %s"
            else:
                query += " AND position_applied = ?"
            params.append(position_filter)
        
        if subcounty_filter_shortlist != "All":
            if is_cloud:
                query += " AND subcounty = %s"
            else:
                query += " AND subcounty = ?"
            params.append(subcounty_filter_shortlist)
        
        if ward_filter != "All":
            if is_cloud:
                query += " AND ward = %s"
            else:
                query += " AND ward = ?"
            params.append(ward_filter)
        
        if gender_filter != "All":
            if is_cloud:
                query += " AND gender = %s"
            else:
                query += " AND gender = ?"
            params.append(gender_filter)
        
        query += " ORDER BY position_applied, name"
        
        # Execute query
        if params:
            if is_cloud:
                shortlisted_df = pd.read_sql(query, conn, params=tuple(params))
            else:
                shortlisted_df = pd.read_sql(query, conn, params=tuple(params))
        else:
            shortlisted_df = pd.read_sql(query, conn)
        
        # Apply age filter
        if not shortlisted_df.empty and 'yob' in shortlisted_df.columns:
            current_year = datetime.now().year
            shortlisted_df['age'] = current_year - shortlisted_df['yob']
            if age_range:
                shortlisted_df = shortlisted_df[
                    (shortlisted_df['age'] >= age_range[0]) & 
                    (shortlisted_df['age'] <= age_range[1])
                ]
        
        if shortlisted_df.empty:
            st.info("No shortlisted candidates found for open positions matching your criteria.")
        else:
            st.success(f"✅ Total Shortlisted (Open Positions): {len(shortlisted_df)}")
            
            # Group by position - COMPACT DISPLAY
            for position, group in shortlisted_df.groupby('position_applied'):
                st.markdown(f"### 📌 {position} ({len(group)})")
                
                # Compact table without extra spacing
                display_group = group.copy()
                if 'yob' in display_group.columns:
                    display_group['Age'] = current_year - display_group['yob']
                
                # FIX: Convert id_number to string and remove decimals
                if 'id_number' in display_group.columns:
                    display_group['id_number'] = display_group['id_number'].astype(str).str.replace('.0', '', regex=False)
                
                # Select columns for display
                display_cols = ['name', 'id_number', 'contact', 'Age', 'gender', 'subcounty', 'ward']
                available_cols = [col for col in display_cols if col in display_group.columns]
                
                # Add delete column to the dataframe display
                st.dataframe(
                    display_group[available_cols],
                    use_container_width=True,
                    height=min(400, len(display_group) * 35 + 38)
                )
                
                # FIX: Improved delete functionality
                if len(display_group) > 0:
                    st.markdown("**🗑️ Delete from Shortlist:**")
                    cols = st.columns(min(len(display_group), 5))
                    for i, (idx, row) in enumerate(display_group.iterrows()):
                        col_idx = i % 5
                        with cols[col_idx]:
                            # Use row ID as key, not name
                            if st.button(f"Delete {row['name'][:12]}", key=f"del_{row['id']}_{position}", use_container_width=True):
                                try:
                                    delete_conn = get_conn()
                                    delete_cursor = delete_conn.cursor()
                                    
                                    # Get candidate details before deleting
                                    if is_cloud:
                                        delete_cursor.execute("""
                                            SELECT name, id_number, position_applied FROM staff WHERE id = %s
                                        """, (row['id'],))
                                    else:
                                        delete_cursor.execute("""
                                            SELECT name, id_number, position_applied FROM staff WHERE id = ?
                                        """, (row['id'],))
                                    
                                    candidate_info = delete_cursor.fetchone()
                                    
                                    # Update status to Pending
                                    if is_cloud:
                                        delete_cursor.execute("""
                                            UPDATE staff 
                                            SET application_status = 'Pending',
                                                shortlist_date = NULL
                                            WHERE id = %s
                                        """, (row['id'],))
                                    else:
                                        delete_cursor.execute("""
                                            UPDATE staff 
                                            SET application_status = 'Pending',
                                                shortlist_date = NULL
                                            WHERE id = ?
                                        """, (row['id'],))
                                    
                                    delete_conn.commit()
                                    delete_conn.close()
                                    
                                    # =========================================================
                                    # AUDIT TRAIL - Log deletion from shortlist
                                    # =========================================================
                                    log_audit(
                                        username=st.session_state.user['username'],
                                        action="REMOVE_SHORTLIST",
                                        record_id=int(row['id']),
                                        details=f"Removed {candidate_info[0]} (ID: {candidate_info[1]}) from shortlist for {candidate_info[2]}",
                                        status="Success"
                                    )
                                    
                                    st.success(f"✅ Removed {candidate_info[0]} from shortlist!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                
                st.markdown("---")
        
            # =========================================================
            # EXPORT OPTIONS WITH AUDIT LOG
            # =========================================================
            st.markdown("### 📥 Export Options")
            
            col1, col2 = st.columns(2)
            with col1:
                csv = shortlisted_df.to_csv(index=False).encode('utf-8')
                if st.download_button(
                    "📥 Download All (CSV)", 
                    csv, 
                    f"shortlisted_open_{datetime.now().strftime('%Y%m%d')}.csv", 
                    "text/csv", 
                    use_container_width=True,
                    key="download_all_shortlisted"
                ):
                    # =========================================================
                    # AUDIT TRAIL - Log export all
                    # =========================================================
                    log_audit(
                        username=st.session_state.user['username'],
                        action="EXPORT_SHORTLIST_ALL",
                        record_id=0,
                        details=f"Exported all {len(shortlisted_df)} shortlisted candidates to CSV",
                        status="Success"
                    )
            
            with col2:
                export_position = st.selectbox("Export Position", ["All"] + sorted(shortlisted_df['position_applied'].dropna().unique().tolist()), key="export_pos")
                if export_position != "All":
                    export_df = shortlisted_df[shortlisted_df['position_applied'] == export_position]
                    csv_pos = export_df.to_csv(index=False).encode('utf-8')
                    if st.download_button(
                        f"📥 Download {export_position}", 
                        csv_pos, 
                        f"shortlisted_{export_position.replace(' ', '_')}.csv", 
                        "text/csv", 
                        use_container_width=True,
                        key="download_position_shortlisted"
                    ):
                        # =========================================================
                        # AUDIT TRAIL - Log export by position
                        # =========================================================
                        log_audit(
                            username=st.session_state.user['username'],
                            action="EXPORT_SHORTLIST_POSITION",
                            record_id=0,
                            details=f"Exported {len(export_df)} shortlisted candidates for position: {export_position}",
                            status="Success"
                        )
    
    except Exception as e:
        st.error(f"Error: {str(e)}")
    finally:
        conn.close()


# FIX 2: In TAB 4, also handle decimal ID numbers for analysis
# Add this after the analysis_df is created:

    # ... existing code ...
    
    # FIX: Convert id_number to string and remove decimals for display
    if 'id_number' in analysis_df.columns:
        analysis_df['id_number'] = analysis_df['id_number'].astype(str).str.replace('.0', '', regex=False)
    
    # ... rest of code continues ...
