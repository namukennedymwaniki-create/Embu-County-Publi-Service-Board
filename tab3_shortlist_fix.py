# FIX FOR TAB 3: SHORTLISTED CANDIDATES
# Replace the entire Tab 3 section with this code:

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
    
    # Search bar for shortlisted candidates
    st.markdown("### 🔍 Search & Filter")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        search_shortlist = st.text_input("Search Name/ID", placeholder="Type name or ID...", key="search_shortlist")
    
    with col2:
        # Only show open positions in filter
        position_list = ["All"] + sorted(open_positions_list) if open_positions_list else ["All"]
        position_filter = st.selectbox("Position", position_list, key="pos_filter")
    
    with col3:
        subcounty_query = "SELECT DISTINCT subcounty FROM staff WHERE application_status = 'Shortlisted' AND subcounty IS NOT NULL"
        subcounty_df = pd.read_sql(subcounty_query, conn)
        subcounty_list = ["All"] + sorted(subcounty_df['subcounty'].dropna().unique().tolist())
        subcounty_filter_shortlist = st.selectbox("Sub-County", subcounty_list, key="sub_filter")
    
    with col4:
        ward_query = "SELECT DISTINCT ward FROM staff WHERE application_status = 'Shortlisted' AND ward IS NOT NULL"
        ward_df = pd.read_sql(ward_query, conn)
        ward_list = ["All"] + sorted(ward_df['ward'].dropna().unique().tolist())
        ward_filter = st.selectbox("Ward", ward_list, key="ward_filter")
    
    with col5:
        gender_list = ["All", "Male", "Female"]
        gender_filter = st.selectbox("Gender", gender_list, key="gender_filter")
    
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
        # CRITICAL FIX: Build query step by step to ensure all data is captured
        query = """
            SELECT id, name, id_number, contact, email, qualifications, experience_years, 
                   application_status, subcounty, position_applied, shortlist_date, 
                   gender, yob, ward
            FROM staff 
            WHERE application_status = 'Shortlisted'
            AND position_applied IS NOT NULL
        """
        
        params = []
        
        # ONLY filter to open positions
        if open_positions_list:
            if is_cloud:
                placeholders = ','.join(['%s'] * len(open_positions_list))
                query += f" AND position_applied IN ({placeholders})"
                params.extend(open_positions_list)
            else:
                placeholders = ','.join(['?'] * len(open_positions_list))
                query += f" AND position_applied IN ({placeholders})"
                params.extend(open_positions_list)
        else:
            # No open positions exist
            st.warning("⚠️ No open advertised positions found. Please create open positions first.")
            conn.close()
            st.stop()
        
        # Apply search filter
        if search_shortlist:
            if is_cloud:
                query += " AND (name ILIKE %s OR id_number::TEXT ILIKE %s)"
                search_pattern = f"%{search_shortlist}%"
                params.extend([search_pattern, search_pattern])
            else:
                query += " AND (name LIKE ? OR id_number LIKE ?)"
                search_pattern = f"%{search_shortlist}%"
                params.extend([search_pattern, search_pattern])
        
        # Apply position filter
        if position_filter != "All":
            if is_cloud:
                query += " AND position_applied = %s"
            else:
                query += " AND position_applied = ?"
            params.append(position_filter)
        
        # Apply subcounty filter
        if subcounty_filter_shortlist != "All":
            if is_cloud:
                query += " AND subcounty = %s"
            else:
                query += " AND subcounty = ?"
            params.append(subcounty_filter_shortlist)
        
        # Apply ward filter
        if ward_filter != "All":
            if is_cloud:
                query += " AND ward = %s"
            else:
                query += " AND ward = ?"
            params.append(ward_filter)
        
        # Apply gender filter
        if gender_filter != "All":
            if is_cloud:
                query += " AND gender = %s"
            else:
                query += " AND gender = ?"
            params.append(gender_filter)
        
        query += " ORDER BY position_applied, name"
        
        # Execute query with parameters
        if params:
            if is_cloud:
                shortlisted_df = pd.read_sql(query, conn, params=tuple(params))
            else:
                shortlisted_df = pd.read_sql(query, conn, params=tuple(params))
        else:
            shortlisted_df = pd.read_sql(query, conn)
        
        # DATA VALIDATION: Ensure no NULL position_applied in results
        if not shortlisted_df.empty:
            initial_count = len(shortlisted_df)
            shortlisted_df = shortlisted_df[shortlisted_df['position_applied'].notna()]
            if len(shortlisted_df) < initial_count:
                st.warning(f"⚠️ Removed {initial_count - len(shortlisted_df)} candidate(s) with missing position data")
        
        if shortlisted_df.empty:
            st.info("No shortlisted candidates found for open positions matching your criteria.")
        else:
            st.success(f"✅ Total Shortlisted (Open Positions): {len(shortlisted_df)}")
            
            # Group by position - FULL DATA DISPLAY
            for position, group in shortlisted_df.groupby('position_applied'):
                st.markdown(f"### 📌 {position} ({len(group)})")
                
                # Prepare display dataframe
                display_group = group.copy()
                
                # Calculate age if yob is available
                current_year = datetime.now().year
                if 'yob' in display_group.columns:
                    display_group['Age'] = current_year - display_group['yob'].astype(float, errors='ignore')
                
                # Define comprehensive column order for display
                display_cols_ordered = [
                    'name', 
                    'id_number', 
                    'contact', 
                    'email',
                    'qualifications',
                    'experience_years',
                    'Age',
                    'gender',
                    'subcounty',
                    'ward',
                    'shortlist_date'
                ]
                
                # Filter to only columns that exist in dataframe
                available_cols = [col for col in display_cols_ordered if col in display_group.columns]
                
                # Rename columns for better display
                display_rename = {
                    'name': 'Name',
                    'id_number': 'ID Number',
                    'contact': 'Phone',
                    'email': 'Email',
                    'qualifications': 'Qualifications',
                    'experience_years': 'Experience (Yrs)',
                    'Age': 'Age',
                    'gender': 'Gender',
                    'subcounty': 'Sub-County',
                    'ward': 'Ward',
                    'shortlist_date': 'Shortlisted Date'
                }
                
                # Create display dataframe
                display_df = display_group[available_cols].copy()
                display_df = display_df.rename(columns=display_rename)
                
                # Format shortlist_date if it exists
                if 'Shortlisted Date' in display_df.columns:
                    display_df['Shortlisted Date'] = pd.to_datetime(
                        display_df['Shortlisted Date'], 
                        errors='coerce'
                    ).dt.strftime('%Y-%m-%d %H:%M')
                
                # Display full table with all data
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=min(400, len(display_group) * 35 + 38)
                )
                
                st.markdown("---")
            
            # EXPORT OPTIONS
            st.markdown("### 📥 Export Options")
            
            col1, col2 = st.columns(2)
            with col1:
                # Export all shortlisted with full details
                export_df = shortlisted_df.copy()
                if 'yob' in export_df.columns:
                    export_df['Age'] = current_year - export_df['yob'].astype(float, errors='ignore')
                
                csv = export_df.to_csv(index=False).encode('utf-8')
                if st.download_button(
                    "📥 Download All (CSV with Full Details)", 
                    csv, 
                    f"shortlisted_open_{datetime.now().strftime('%Y%m%d')}.csv", 
                    "text/csv", 
                    use_container_width=True,
                    key="download_all_shortlisted"
                ):
                    log_audit(
                        username=st.session_state.user['username'],
                        action="EXPORT_SHORTLIST_ALL",
                        record_id=0,
                        details=f"Exported all {len(export_df)} shortlisted candidates with full details to CSV",
                        status="Success"
                    )
            
            with col2:
                export_position = st.selectbox("Export Position", ["All"] + sorted(shortlisted_df['position_applied'].dropna().unique().tolist()), key="export_pos")
                if export_position != "All":
                    export_df = shortlisted_df[shortlisted_df['position_applied'] == export_position].copy()
                    if 'yob' in export_df.columns:
                        export_df['Age'] = current_year - export_df['yob'].astype(float, errors='ignore')
                    
                    csv_pos = export_df.to_csv(index=False).encode('utf-8')
                    if st.download_button(
                        f"📥 Download {export_position}", 
                        csv_pos, 
                        f"shortlisted_{export_position.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv", 
                        "text/csv", 
                        use_container_width=True,
                        key="download_position_shortlisted"
                    ):
                        log_audit(
                            username=st.session_state.user['username'],
                            action="EXPORT_SHORTLIST_POSITION",
                            record_id=0,
                            details=f"Exported {len(export_df)} shortlisted candidates for position: {export_position}",
                            status="Success"
                        )
    
    except Exception as e:
        st.error(f"Error loading shortlisted candidates: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
    finally:
        conn.close()
