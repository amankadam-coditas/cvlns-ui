import streamlit as st
import requests
import pandas as pd
from PIL import Image
import io

# --- Page Config ---
st.set_page_config(
    page_title="Civic Lens | AI Grievance Reporting", page_icon="🏙️", layout="wide"
)

# --- Sidebar & API Config ---
st.sidebar.title("🏙️ Civic Lens")
st.sidebar.write("AI-Powered Civic Grievance Reporting System")
API_BASE_URL = st.sidebar.text_input("API Base URL", "https://qrhb803g-8000.inc1.devtunnels.ms")

st.sidebar.markdown("---")
# Health Check
if st.sidebar.button("Check API Health"):
    try:
        res = requests.get(f"{API_BASE_URL}/health")
        if res.status_code == 200:
            st.sidebar.success("✅ API is Online")
        else:
            st.sidebar.error("❌ API Offline/Error")
    except requests.exceptions.ConnectionError:
        st.sidebar.error("❌ Cannot connect to API")


# --- Helper Functions ---
@st.cache_data(ttl=60)
def get_categories():
    try:
        res = requests.get(f"{API_BASE_URL}/api/complaints/categories")
        if res.status_code == 200:
            data = res.json()
            # API returns {"categories": [...]}; normalize to a list
            if isinstance(data, dict):
                cats = data.get("categories") or data.get("category")
                if isinstance(cats, list):
                    return cats
            if isinstance(data, list):
                return data
    except:
        pass
    return ["Road", "Municipal", "Electricity", "Water"]  # Fallback


@st.cache_data(ttl=60)
def get_departments():
    try:
        res = requests.get(f"{API_BASE_URL}/api/complaints/departments")
        if res.status_code == 200:
            data = res.json()
            # API returns {"departments": [...]}; normalize to a list
            if isinstance(data, dict):
                depts = data.get("departments") or data.get("department")
                if isinstance(depts, list):
                    return depts
            if isinstance(data, list):
                return data
    except:
        pass
    return ["Public Works", "Sanitation", "Water Board", "Power Dept"]  # Fallback


# --- Main UI Layout ---
st.title("Civic Lens Dashboard")

tab1, tab2, tab3 = st.tabs(
    ["📢 Submit Complaint", "🔍 Track Complaint", "🏛️ Department Dashboard"]
)

# ==========================================
# TAB 1: SUBMIT COMPLAINT
# ==========================================
with tab1:
    st.header("Report a Civic Issue")

    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader(
            "Upload Image of the Issue*", type=["jpg", "jpeg", "png"]
        )

        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Image", use_container_width=True)

            # Image Validation Endpoint Integration
            if st.button("Validate Image Quality (AI)"):
                with st.spinner("Analyzing image quality..."):
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type,
                        )
                    }
                    try:
                        val_res = requests.post(
                            f"{API_BASE_URL}/api/complaints/validate-image", files=files
                        )
                        if val_res.status_code == 200:
                            st.success("✅ Image quality is good for submission.")
                        else:
                            st.warning(f"⚠️ Validation warning: {val_res.text}")
                    except Exception as e:
                        st.error("API connection failed.")

    with col2:
        st.subheader("Location & Details")

        # Location (Mocking GPS capture)
        loc_col1, loc_col2 = st.columns(2)
        with loc_col1:
            lat = st.number_input("Latitude*", value=0.000000, format="%.6f")
        with loc_col2:
            lng = st.number_input("Longitude*", value=0.000000, format="%.6f")

        category = st.selectbox("Category (Optional)", ["None"] + get_categories())
        description = st.text_area(
            "Description (Optional)", placeholder="Briefly describe the issue..."
        )

        if st.button("🚀 Submit Complaint", type="primary"):
            if uploaded_file is None:
                st.error("Please upload an image.")
            elif lat == 0.0 or lng == 0.0:
                st.error("Please provide valid coordinates.")
            else:
                with st.spinner("AI is processing your complaint..."):
                    # Prepare multipart/form-data
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            uploaded_file.type,
                        )
                    }
                    data = {
                        "latitude": lat,
                        "longitude": lng,
                    }
                    if category != "None":
                        data["category"] = category
                    if description:
                        data["description"] = description

                    try:
                        res = requests.post(
                            f"{API_BASE_URL}/api/complaints/submit",
                            files=files,
                            data=data,
                        )
                        if res.status_code == 200:
                            result = res.json()
                            st.success(
                                f"Complaint successfully registered! ID: **{result['complaint_id']}**"
                            )

                            # Show AI Analysis Results
                            st.info(
                                f"**AI Detected Category:** {result.get('category_ai')}"
                            )
                            st.info(
                                f"**Assigned Department:** {result.get('department')}"
                            )
                            st.progress(
                                result.get("ai_confidence", 0.0),
                                text=f"AI Confidence: {result.get('ai_confidence', 0.0)*100:.1f}%",
                            )

                            if result.get("consistency_status") != "CONSISTENT":
                                st.warning(
                                    f"Consistency Check: {result.get('consistency_status')}"
                                )

                        else:
                            st.error(f"Error submitting complaint: {res.text}")
                    except Exception as e:
                        st.error(f"Connection error: {e}")

# ==========================================
# TAB 2: TRACK COMPLAINT
# ==========================================
with tab2:
    st.header("Check Complaint Status")

    complaint_id = st.text_input("Enter Complaint ID")

    if st.button("Check Status"):
        if not complaint_id:
            st.warning("Please enter a Complaint ID.")
        else:
            with st.spinner("Fetching details..."):
                try:
                    res = requests.get(
                        f"{API_BASE_URL}/api/complaints/status/{complaint_id}"
                    )
                    if res.status_code == 200:
                        data = res.json()

                        st.subheader(f"Complaint: {data['complaint_id']}")

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Status", data["status"])
                        col2.metric("Department", data["department"])
                        col3.metric("AI Category", data["category_ai"])

                        st.write("---")

                        det_col1, det_col2 = st.columns([1, 2])
                        with det_col1:
                            if data.get("image_url"):
                                # Fallback to text if actual URL serving isn't set up
                                st.write(f"**Image URL:** {data['image_url']}")
                            st.write(f"**Timestamp:** {data['timestamp']}")
                            st.write(
                                f"**Location:** Lat {data['location']['latitude']}, Lng {data['location']['longitude']}"
                            )

                        with det_col2:
                            st.write(
                                "**User Description:**",
                                data.get("description_user", "N/A"),
                            )
                            st.write(
                                "**AI Generated Description:**",
                                data.get("description_generated", "N/A"),
                            )
                            st.write(
                                f"**Consistency:** {data.get('consistency_status')} (Score: {data.get('consistency_score')})"
                            )

                            with st.expander("View Raw AI Analysis Data"):
                                st.json(data.get("image_analysis_results", {}))

                    elif res.status_code == 404:
                        st.error("Complaint not found.")
                    else:
                        st.error(f"Error: {res.text}")
                except Exception as e:
                    st.error(f"Connection error: {e}")

# ==========================================
# TAB 3: DEPARTMENT DASHBOARD
# ==========================================
with tab3:
    st.header("Department Admin Dashboard")

    view_type = st.radio("View", ["All Complaints", "By Department"], horizontal=True)

    fetch_url = f"{API_BASE_URL}/api/complaints/list"

    if view_type == "By Department":
        selected_dept = st.selectbox("Select Department", get_departments())
        fetch_url = f"{API_BASE_URL}/api/complaints/department/{selected_dept}"

    col1, col2 = st.columns(2)
    with col1:
        skip = st.number_input("Skip (Pagination)", value=0, min_value=0)
    with col2:
        limit = st.number_input("Limit", value=50, min_value=1, max_value=100)

    if st.button("Refresh Data"):
        with st.spinner("Fetching records..."):
            try:
                res = requests.get(fetch_url, params={"skip": skip, "limit": limit})
                if res.status_code == 200:
                    records = res.json()
                    if len(records) > 0:
                        # Flatten dictionary for dataframe
                        df = pd.json_normalize(records)
                        # Reorder columns for better readability
                        cols_to_show = [
                            "complaint_id",
                            "status",
                            "department",
                            "category_ai",
                            "timestamp",
                            "consistency_status",
                        ]
                        # Filter to available columns
                        cols_to_show = [c for c in cols_to_show if c in df.columns]

                        st.dataframe(df[cols_to_show], use_container_width=True)
                    else:
                        st.info("No complaints found for this selection.")
                else:
                    st.error("Failed to fetch records.")
            except Exception as e:
                st.error("Connection error.")

    st.write("---")
    st.subheader("Update Complaint Status")
    upd_col1, upd_col2, upd_col3 = st.columns(3)

    with upd_col1:
        update_id = st.text_input("Complaint ID to Update")
    with upd_col2:
        # Based on StatusEnum from OpenAPI
        new_status = st.selectbox("New Status", ["Registered", "Forwarded", "Closed"])
    with upd_col3:
        st.write("")  # spacing
        st.write("")  # spacing
        if st.button("Update Status", type="primary"):
            if update_id:
                try:
                    res = requests.put(
                        f"{API_BASE_URL}/api/complaints/status/{update_id}",
                        params={"status": new_status},
                    )
                    if res.status_code == 200:
                        st.success(f"Successfully updated {update_id} to {new_status}")
                    else:
                        st.error(f"Failed to update: {res.text}")
                except Exception as e:
                    st.error("Connection error.")
            else:
                st.warning("Please enter a Complaint ID.")
