import streamlit as st
import os
import sys
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.analyst_agent import AnalystAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.interpreter_agent import InterpreterAgent
from src.agents.report_agent import ReportGeneratorAgent
from src.agents.distributor_agent import DistributorAgent

# Load Environment Variables
load_dotenv()

# Page Config
st.set_page_config(
    page_title="Incrementality Analysis Orchestrator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS
def load_css():
    with open(os.path.join(os.path.dirname(__file__), 'style.css')) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

# Sidebar
with st.sidebar:
    st.title("Configuration")
    st.markdown("---")
    
    st.subheader("Data Source")
    table_name = st.text_input("Snowflake Table", value="PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.INCREMENTALITY_ANALYSIS_DUMMY")
    
    st.subheader("Analysis Parameters")
    treatment = st.text_input("Treatment Column", value="received_email")
    outcome = st.text_input("Outcome Column", value="converted")
    
    # RESTRICTED METHOD SELECTION as requested
    method = st.selectbox("Method", ["logistic_regression"], help="Currently only Logistic Regression is supported for stability.")
    
    st.markdown("---")
    st.caption("GCP Reporting Orchestrator v1.0")

# Main Content
st.title("GCP Reporting Orchestrator")
st.markdown("### Incrementality Analysis Pipeline")

# Input Section
col1, col2 = st.columns([3, 1])
with col1:
    business_question = st.text_input(
        "Business Question", 
        value="What is the incremental lift in conversions from the LNP email campaign?",
        placeholder="e.g., Did the summer campaign increase sales?"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True) # Spacer
    run_btn = st.button("RUN ANALYSIS", type="primary", use_container_width=True)

# Execution Logic
if run_btn:
    # Prepare Request
    request_data = {
        'table': table_name,
        'treatment': treatment,
        'outcome': outcome,
        'covariates': ['age_group', 'customer_segment', 'total_purchases', 'recency_bin'], # Hardcoded for demo, could be dynamic
        'method': method,
        'business_question': business_question
    }

    # Container for results
    results_container = st.container()
    
    with results_container:
        # Progress Tracking
        status_text = st.empty()
        progress_bar = st.progress(0)
        
        # Detailed Log Expander
        log_expander = st.expander("Detailed Execution Log", expanded=True)
        
        def log(message):
            timestamp = datetime.now().strftime("%H:%M:%S")
            log_expander.text(f"[{timestamp}] {message}")

        try:
            # Step 1: Analyst Agent
            status_text.markdown("#### 🤖 Step 1: Analyst Agent (Gemini)")
            log("Starting Analyst Agent...")
            log(f"Generating analysis code for question: '{business_question}'")
            log(f"Method: {method}")
            
            analyst = AnalystAgent(semantic_model_path='docs/semantic_model.yaml')
            analyst_result = analyst.generate_analysis_code(request_data)
            code = analyst_result['code']
            log("Analysis code generated successfully.")
            
            progress_bar.progress(20)
            with st.expander("View Generated Code"):
                st.code(code, language='python')
                
            # Step 2: Executor Agent
            status_text.markdown("#### ⚙️ Step 2: Executor Agent (Snowpark)")
            log("Starting Executor Agent...")
            log("Connecting to Snowflake...")
            
            executor = ExecutorAgent()
            if analyst_result.get('gcs_path'):
                log(f"Executing script from GCS: {analyst_result['gcs_path']}")
                execution_result = executor.execute_from_gcs(analyst_result['gcs_path'])
            else:
                log("Executing script directly...")
                execution_result = executor.execute_code(code)
                
            if not execution_result['success']:
                # Extract error from various possible locations
                error_msg = execution_result.get('error')
                if not error_msg:
                    error_msg = execution_result.get('stderr')
                if not error_msg and execution_result.get('analysis_results'):
                    error_msg = execution_result['analysis_results'].get('error')
                if not error_msg:
                    error_msg = "Unknown execution error"
                    
                log(f"ERROR: Execution failed. {error_msg}")
                st.error(f"Execution Failed: {error_msg}")
                st.stop()
            
            log("Execution successful.")
            analysis_data = execution_result['analysis_results']
            log(f"Analysis Results: {json.dumps(analysis_data, indent=2)}")
            progress_bar.progress(40)
            
            # Step 3: Interpreter Agent
            status_text.markdown("#### 🧠 Step 3: Interpreter Agent (Claude)")
            log("Starting Interpreter Agent...")
            log("Interpreting statistical results...")
            
            interpreter = InterpreterAgent()
            insights = interpreter.interpret_and_store(analysis_data)
            log("Insights generated.")
            progress_bar.progress(60)
            
            # Step 4: Reporter Agent
            status_text.markdown("#### 📄 Step 4: Reporter Agent (Gemini)")
            log("Starting Reporter Agent...")
            log("Generating persona-specific PDF reports...")
            
            reporter = ReportGeneratorAgent()
            reports = reporter.generate_all_persona_reports(insights, output_format='pdf')
            log(f"Reports generated for: {', '.join(reports.keys())}")
            progress_bar.progress(80)
            
            # Step 5: Distributor Agent
            status_text.markdown("#### 📨 Step 5: Distributor Agent")
            log("Starting Distributor Agent...")
            log("Distributing reports to stakeholders...")
            
            distributor = DistributorAgent()
            distribution_results = distributor.distribute_reports(
                all_reports=reports,
                insights=insights,
                metadata={
                    'request': request_data,
                    'analyst_result': analyst_result,
                    'execution_result': execution_result
                }
            )
            log("Distribution complete.")
            progress_bar.progress(100)
            status_text.markdown("#### ✅ Analysis Complete")
            
            # Display Results
            st.markdown("---")
            st.subheader("Key Results")
            
            # Extract metrics from raw_analysis if available, otherwise try top-level
            raw_metrics = insights.get('raw_analysis', insights)
            
            m1, m2, m3 = st.columns(3)
            with m1:
                lift = raw_metrics.get('incremental_lift_pct', 0)
                st.metric("Incremental Lift", f"{lift:.2f}%")
            with m2:
                pval = raw_metrics.get('p_value', 1.0)
                st.metric("Statistical Significance (P-Value)", f"{pval:.5f}")
            with m3:
                # Handle both boolean and integer (1/0) for significance
                sig_val = raw_metrics.get('is_significant', 0)
                sig = "Yes" if sig_val else "No"
                st.metric("Significant?", sig)
                
            st.markdown("### Generated Reports")
            r1, r2, r3 = st.columns(3)
            
            with r1:
                st.markdown("**CMO Report**")
                st.success("Sent to CMO")
                
            with r2:
                st.markdown("**Marketing Ops Report**")
                st.success("Sent to Teams")
                
            with r3:
                st.markdown("**Data Team Report**")
                st.success("Sent to Data Team")
                
            with st.expander("View Detailed Insights"):
                st.json(insights)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            log(f"CRITICAL ERROR: {str(e)}")

else:
    st.info("Configure your analysis parameters in the sidebar and click 'RUN ANALYSIS' to start.")
    
    # Placeholder for visual balance
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 🎯 Precision")
        st.caption("Causal inference methods for accurate lift measurement.")
    with c2:
        st.markdown("#### ⚡ Speed")
        st.caption("Automated end-to-end pipeline from SQL to PDF.")
    with c3:
        st.markdown("#### 🤝 Alignment")
        st.caption("Tailored reports for every stakeholder persona.")
