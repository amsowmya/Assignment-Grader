import streamlit as st 
import requests 
import json 
import os 
import tempfile 
import time 
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

openai_api_key = os.environ.get('OPENAI_API_KEY', '')
google_api_key = os.environ.get('GOOGLE_API_KEY', '')
search_engine_id = os.environ.get('SEARCH_ENGINE_ID', '')

# Initialize session state variables
if 'api_server_url' not in st.session_state:
    st.session_state['api_server_url'] = "http://localhost:8088"
    
# Always use our hardcoded keys - don't get them from session_state
st.session_state['openai_api_key'] = openai_api_key
st.session_state['google_api_key'] = google_api_key
st.session_state['search_engine_id'] = search_engine_id

# Function to call API tools 
def call_api_tool(tool_name, data):
    """Call a tool on the API server with hardcoded API keys."""
    url = f"{st.session_state['api_server_url']}/tools/{tool_name}"
    
    # Create a copy of the data 
    request_data = data.copy() 
    
    # ALWAYS add API keys to EVERY request
    request_data['openai_api_key'] = openai_api_key
    request_data['google_api_key'] = google_api_key
    request_data['search_engine_id'] = search_engine_id
    
    # Log the API call (but hide most of the keys)
    log_data = request_data.copy()
    if "openai_api_key" in log_data:
        log_data['openai_api_key'] = f"{key[:5]}...{key[-5:]}"
        key = log_data['openai_api_key']
    if "google_api_key" in log_data:
        key = log_data['google_api_key']
        log_data['google_api_key'] = f"{key[:5]}...{key[-5:]}"
        
    logger.info(f"Calling {tool_name} with data: {json.dumps(log_data)}")
    
    try:
        response = requests.post(
            url,
            json=request_data,
            headers={"Context-Type": "application/json"},
            timeout=60
        )
        
        if response.status_code != 200:
            error_message = f"Error {response.status_code} from server: {response.text}"
            logger.error(error_message)
            st.error(error_message)
            return None 
        
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text
        
    except Exception as e:
        error_message = f"Error conecting to server: {str(e)}"
        logger.error(error_message)
        st.error(error_message)
        return None


st.set_page_config(
    page_title="Assignment Grader",
    page_icon="",
    layout="wide"
)

# Main title 
st.title("Assignment Grader")
st.markdown("Upload assignment and grade them automatically with AI")

st.sidebar.header("About")
st.sidebar.info(""" 
                This is a demo of the Assignment Grader using FastMCP  and openAI.
                Upload assignments in PDF and DOCX format, set your grading rubric,
                and get instant AI-powered grades with detailed feedback.
                """)

# create tabs 
tab1, tab2, tab3 = st.tabs(["Upload Assignment", "Grade Assignment", "Results"])

with tab1:
    st.header("Upload Assignment")
    
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])
    
    if uploaded_file is not None:
        # Save the uploaded file temporararily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            file_path = tmp_file.name
            
        st.session_state['file_path'] = file_path
        st.session_state['file_name'] = uploaded_file.name 
        
        if st.button("Process Document"):
            with st.spinner("Processing document..."):
                result = call_mcp_tool("parse_file", {"file_path": file_path})
                
                if result is None:
                    st.error("Failed to process document. Check server connection")
                elif isinstance(result, str):
                    st.session_state['document_text'] = result 
                    st.success(f"Document processed successfully!")
                    st.info(f"Document contains {len(result.split)} words.")
                    
                    with st.expander("Document Preview"):
                        st.text(result[:1000] + ("..." if len(result) > 1000 else ""))
                else:
                    st.session_state['document_text'] = str(result)
                    st.success(f"Document processed!")
                    
                    with st.expander("Document Preview"):
                        st.join(result)
    
with tab2:
    st.header("Grading Configuration")
    
    # Rubric input 
    st.subheader("Grading Rubric")
    rubric = st.text_area(
        "Enter your grading rubric here:",
        height=200,
        help="Specify the criteria on which the assignment should be graded",
        value="""Content (40%): The assignment should demonstrate a through understanding of the topic.
        Structure (20%): The assignment should be well-organized with a clear introduction, body, and conclusion.
        Analysis (30%): The assignment should include critical analysis backed by evidence.
        Grammer & Style (10%): The assignment should be free of grammatical errors and use appropriate academic language.
        
        """
    )
    
    # Plagiarism check option 
    check_plagirism_option = st.checkbox("Check for plagiarism", value=True)
    
    if 'document_text' in st.session_state and st.button("Grade Assignment"):
        # Store rubric in session 
        st.session_state['rubric'] = rubric 
        
        with st.spinner("Grading in progress..."):
            # Optional plagiarism check 
            if check_plagirism_option:
                st.info("Checking for plagiarism")
                plagiarism_results = call_mcp_tool("check_plagiarism", {"text": st.session_state['document_Text']})
                st.session_state['plagiarism_results'] = plagiarism_results 
                if plagiarism_results is None:
                    st.warning("Plagiarism check failed or returned no results.")
                    
            # Generate grade 
            st.info("Generating grade...")
            grade_results = call_mcp_tool("grade_text", {
                "text": st.session_state['document_text'],
                "rubric": rubric 
            })
            st.session_state['grade_results'] = grade_results
            if grade_results is None:
                st.warning("Grade generation failed or returned no results.")
                
            # Generate feedback 
            st.info("Generating feedback...")
            feedback = call_mcp_tool("generate_feedback", {
                "text": st.session_state['document_text'],
                "rubric": rubric
            })
            
            st.session_state['feedback'] = feedback
            if feedback is None:
                st.warning("Feedback generation failed or returned no results.")
                
            if grade_results is not None or feedback is not None:
                st.success("Grading completed!")
                st.balloons()
                
            else:
                st.error("Grading process encountered errors. Please check your server connection and API settings")
                
# Tab 3: Results 
with tab3:
    st.header("Grading Results")
    
    if all(k in st.session_state for k in ['file_name', 'grade_results', 'feedback']):
        st.subheader(f"Results for: {st.session_state['file_name']}")
        
        # Display grade 
        if 'grade_results' in st.session_state:
            if st.session_state['grade_results'] is not None:
                grade = st.session_state['grade_results'].get('grade', 'Not available')
                st.metric("Grade", grade)
            else:
                st.warning("Grade information is not available. There might have been an error during grading.")
                st.metric("Grade", "Not available")
                
        # Display feedback 
        if 'feedback' in st.session_state:
            if st.session_state['feedback'] is not None:
                st.subheader("Feedback")
                st.markdown(st.session_state['feedback'])
            else:
                st.warning("Feedback is not available.There might have been an error during generating feedback.")
                
        # Display plagiarism results if available
        if 'plagiarism_results' in st.session_state and st.session_state['plagiarism_results']:
            st.subheader("Plagiarism Check")
            results = st.session_state['plagiarism_results']
            
            if results is None:
                st.warning("Plagiarism check results are not available. There might have been an error during the check.")
            elif 'error' in results:
                st.error(f"Plagiarism check error: {results['error']}")
            else:
                st.markdown("**Similarity matches found:**")
                for url, similarity in results.items():
                    if similarity >70:
                        st.warning(f"High similarity ({similarity}%): [{url}]({url})")
                    elif similarity > 40:
                        st.info(f"Moderate similarity ({similarity}%): [{url}]({url})")
                    else:
                        st.success(f"Low similarity ({similarity}%): [{url}]({url})")
                        
        # Export options 
        st.subheader("Export Options")
        if st.button("Export to PDF"):
            st.info("PDF export functionaliry would go here")
            
        if st.button("Save to Database"):
            st.info("Database save functionality would go here")
    else:
        st.info("No grading results available. Please upload and grade an assignment first.")
        
        
# API key input 
with st.sidebar.expander("API Configuration"):
    openai_key = st.text_input("OpenAI API key", type="password",
                               help="Your OpenAI API key for grading")
    groq_key = st.text_input("Groq API Key", type="password",
                             help="Your Groq API key for plagiarism detection")
    google_key = st.text_input("Google API Key", type="password",
                               help="Your Google API key for plagiarism detection")
    google_cx = st.text_input("Google Search Engine ID", type="password",
                              help="Your Google Custom Search Engine ID")
    
    if st.button("Save API Settings"):
        # Here you would update the server config, but for now we just acknowledge
        st.success("API settings saved")