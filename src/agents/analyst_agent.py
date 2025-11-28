"""
Agent 1: Data Analyst Agent (Gemini 2.0 Flash)
Generates statistical analysis code for incrementality analysis
"""

import google.generativeai as genai
import yaml
import os
import json
from datetime import datetime
from google.cloud import storage

class AnalystAgent:
    """
    Data Analyst Agent using Gemini 2.0 Flash
    Generates Python code for statistical analysis
    """
    
    def __init__(self, semantic_model_path=None):
        """Initialize the analyst agent"""
        # Remove invalid GOOGLE_APPLICATION_CREDENTIALS if present
        # We use Application Default Credentials instead
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if cred_path and not os.path.exists(cred_path):
                print(f"Removing invalid GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
                del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        # Configure Gemini
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        
        # Configure safety settings to avoid blocking code generation
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
        ]

        self.model = genai.GenerativeModel(
            'gemini-2.5-flash',
            generation_config={
                'temperature': 0.1,  # Low temperature for deterministic code
                'top_p': 0.95,
                'max_output_tokens': 16384,
            },
            safety_settings=safety_settings
        )
        
        # Load semantic model
        self.semantic_model = self._load_semantic_model(semantic_model_path)
        
    def _load_semantic_model(self, path=None):
        """Load semantic model from file or GCS"""
        if path and path.startswith('gs://'):
            # Load from GCS using Application Default Credentials
            client = storage.Client()  # Will use ADC automatically
            bucket_name = path.split('/')[2]
            blob_path = '/'.join(path.split('/')[3:])
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            content = blob.download_as_text()
            return yaml.safe_load(content)
        elif path:
            # Load from local file
            with open(path, 'r') as f:
                return yaml.safe_load(f)
        else:
            # Load from default location, prioritize v2
            paths_to_try = [
                'semantic_model_mvp_v2.yaml',
                'docs/semantic_model_mvp_v2.yaml',
                'docs/semantic_model.yaml'
            ]
            
            for p in paths_to_try:
                if os.path.exists(p):
                    print(f"Loading semantic model from: {p}")
                    with open(p, 'r') as f:
                        return yaml.safe_load(f)
            
            raise FileNotFoundError("Semantic model not found")
    
    def generate_analysis_code(self, analysis_request):
        """
        Generate statistical analysis code
        
        Args:
            analysis_request: Dict with:
                - table: Full table path
                - treatment: Treatment variable name
                - outcome: Outcome variable name
                - covariates: List of covariate names
                - method: Analysis method (psm, did, etc.)
                - business_question: Optional business context
                
        Returns:
            Dict with generated code and metadata
        """
        print(f"Generating analysis code for: {analysis_request.get('business_question', 'Incrementality Analysis')}")
        
        # Build prompt
        prompt = self._build_prompt(analysis_request)
        
        # Generate code with retry logic for syntax errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                generated_code = response.text
                
                # Extract code from markdown if present
                generated_code = self._extract_code(generated_code)
                
                # Validate syntax
                is_valid, error = self._validate_code(generated_code)
                
                if not is_valid:
                    print(f"⚠ WARNING: Syntax error in generated code (attempt {attempt + 1}/{max_retries}): {error}")
                    if attempt < max_retries - 1:
                        print("   Retrying code generation...")
                        continue
                    else:
                        print("   Max retries reached. Returning code with syntax error.")
                else:
                    print("✓ Code syntax validated successfully")
                
                # Save to GCS with fixed name (overwrite latest)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                gcs_path = self._save_to_gcs(generated_code, "latest_analysis_code.py")
                
                return {
                    'code': generated_code,
                    'timestamp': timestamp,
                    'model': 'gemini-2.5-flash',
                    'semantic_model_version': self.semantic_model.get('metadata', {}).get('version', '1.0'),
                    'gcs_path': gcs_path,
                    'is_valid': is_valid,
                    'validation_error': error if not is_valid else None
                }
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠ Generation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    print("   Retrying...")
                    continue
                else:
                    print(f"ERROR: Failed to generate code after {max_retries} attempts: {e}")
                    raise
    
    def _build_prompt(self, request):
        
        prompt = f"""
You are an expert data scientist specializing in causal inference and incrementality analysis.

SEMANTIC MODEL:
{yaml.dump(self.semantic_model, default_flow_style=False)}

ANALYSIS REQUEST:
- Table: {request['table']}
- Treatment Variable: {request['treatment']}
- Outcome Variable: {request['outcome']}
- Covariates: {', '.join(request['covariates'])}
- Method: {request['method']}
- Business Question: {request.get('business_question', 'Measure incremental impact')}

TASK:
Generate a Python script body for a Snowflake Stored Procedure that:

1. **Defines a Handler Function**
   - Import necessary modules: `import snowflake.snowpark`
   - Define a function named `main(session)`
   - The function accepts a `snowflake.snowpark.Session` object
   - Do NOT try to connect to Snowflake manually (use the provided session)
   
2. **Data Loading & Validation**
   - Load data using `df = session.table("{request['table']}").to_pandas()`
   - **STRICTLY FORBIDDEN**: Do NOT use `pd.DataFrame(session.table(...).collect(), columns=...)`. This causes shape mismatches.
   - **STRICTLY FORBIDDEN**: Do NOT hardcode column lists for DataFrame creation.
   - **CRITICAL**: Immediately normalize columns: `df.columns = [c.lower() for c in df.columns]`
   - **DO NOT** validate the total number of columns (df.shape[1]) - just check that required columns exist
   - Check for null values in key columns (treatment, outcome, covariates)
   - Validate treatment/outcome distributions

2.5 **Feature Engineering & Encoding**
   - **CRITICAL**: Identify ALL columns with object/string data types:
     ```python
     categorical_cols = df.select_dtypes(include=['object', 'string']).columns.tolist()
     # Remove treatment/outcome from categorical list if they are there (they should be numeric)
     categorical_cols = [c for c in categorical_cols if c not in [treatment, outcome]]
     ```
   - Apply One-Hot Encoding to ALL categorical columns:
     ```python
     if categorical_cols:
         df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
     ```
   - **CRITICAL**: Sanitize column names to remove spaces and special characters:
     ```python
     def sanitize(name):
         return name.replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_')
     
     df.columns = [sanitize(c) for c in df.columns]
     treatment = sanitize(treatment)
     outcome = sanitize(outcome)
     ```
   - **FINAL CHECK**: Ensure all columns used for modeling are numeric. Drop any remaining non-numeric columns.
   - Define `final_covariates` dynamically:
     ```python
     # All columns except treatment, outcome, and const
     final_covariates = [c for c in df.columns if c not in [treatment, outcome, 'const']]
     ```
   - **DATA CLEANING** (CRITICAL to prevent inf/nan errors):
     ```python
     # Handle missing values
     for col in final_covariates + [treatment, outcome]:
         if df[col].isnull().any():
             if df[col].dtype in ['float64', 'int64']:
                 df[col].fillna(df[col].median(), inplace=True)
             else:
                 df[col].fillna(df[col].mode()[0], inplace=True)
     
     # Replace infinite values with NaN, then fill
     df.replace([np.inf, -np.inf], np.nan, inplace=True)
     for col in final_covariates + [treatment, outcome]:
         if df[col].isnull().any():
             df[col].fillna(df[col].median(), inplace=True)
     
     # Remove columns with zero variance (constant columns cause issues)
     # Remove columns with zero variance (constant columns cause issues)
     from sklearn.feature_selection import VarianceThreshold
     selector = VarianceThreshold(threshold=0.0)
     X_temp = df[final_covariates]
     if not X_temp.empty:
         try:
             selector.fit(X_temp)
             # Only filter if we don't lose EVERYTHING
             supported_indices = selector.get_support(indices=True)
             if len(supported_indices) > 0:
                 final_covariates = [final_covariates[i] for i in supported_indices]
             else:
                 # Fallback: Keep all covariates if cleaning would remove everything (likely mock data issue)
                 pass 
         except ValueError:
             pass # Keep original covariates if fit fails
     ```
   
3. **Propensity Score Matching** (if method == 'psm')
   - Calculate propensity scores using logistic regression
   - Match treated and control units using nearest neighbor (1:1)
   - Check covariate balance after matching
   
4. **Calculate Treatment Effects**
   - For Logistic Regression, use statsmodels.api.Logit:
     ```python
     import statsmodels.api as sm
     # Ensure X is numeric
     X = df[final_covariates + [treatment]].astype(float)
     X = sm.add_constant(X)
     y = df[outcome].astype(float)
     try:
         model = sm.Logit(y, X)
         results = model.fit(disp=0)
         
         # Extract results safely using positional indexing (.iloc)
         treatment_idx = list(X.columns).index(treatment)
         
         p_value = float(results.pvalues.iloc[treatment_idx])
         coef = float(results.params.iloc[treatment_idx])
         conf_int = results.conf_int().iloc[treatment_idx].tolist()
     except Exception as e:
         # Fallback to simple T-test if logistic regression fails (e.g. Singular Matrix)
         print(f" Logistic Regression failed ({{str(e)}}). Falling back to simple T-test.")
         from scipy import stats
         treated = df[df[treatment] == 1][outcome]
         control = df[df[treatment] == 0][outcome]
         t_stat, p_value = stats.ttest_ind(treated, control)
         coef = treated.mean() - control.mean()
         conf_int = [coef - 1.96*0.05, coef + 1.96*0.05] # Approx CI
     ```
   - Calculate Average Treatment Effect (ATE)
   - Calculate confidence intervals (95%)
   - Extract p-values for statistical significance using `.pvalues` attribute
   
5. **Diagnostic Checks**
   - Common support overlap
   - Covariate balance before/after matching
   - Standardized mean differences
   
6. **Return Structured Results**
   - The `main` function MUST return a Python dictionary (which Snowflake converts to VARIANT)
   - **CRITICAL**: Convert all boolean values to integers (1 for True, 0 for False) before returning
   - Do NOT print to stdout (it won't be captured)
   - Return format:
     {{
       "status": "success",
       "treatment_effect": float,
       "p_value": float,
       "confidence_interval": [lower, upper],
       "treated_conversion_rate": float,
       "control_conversion_rate": float,
       "incremental_lift_pct": float,
       "sample_sizes": dict,
       "is_significant": int (1 or 0, NOT bool),
       "diagnostics": dict
     }}

REQUIREMENTS:
- Use these libraries: snowflake.snowpark, pandas, numpy, scipy.stats, sklearn
- **CRITICAL**: Do NOT use `np.float_`, `np.int_`, or `np.bool_`. These are removed in NumPy 2.0. Use `np.float64`, `np.int64`, or native `float`/`int`/`bool`.
- Include comprehensive error handling (return {{"status": "error", "error": str(e)}} on failure)
- **CRITICAL**: Convert ALL boolean values to int (1/0) before returning (Snowflake VARIANT doesn't support Python bool)
- Do NOT use `session.logger` or print statements (they won't work/be captured)
- Do NOT include `if __name__ == "__main__":` block

Generate ONLY the Python code, no markdown formatting.
"""
        return prompt
    def _extract_code(self, text):
        """Extract code from markdown code blocks"""
        if '```python' in text:
            return text.split('```python')[1].split('```')[0].strip()
        elif '```' in text:
            return text.split('```')[1].split('```')[0].strip()
        return text.strip()
    
    def _validate_code(self, code):
        """Validate Python syntax"""
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, str(e)
    
    def _save_to_gcs(self, content, filename):
        """Save generated code to GCS using Application Default Credentials"""
        try:
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            if not bucket_name:
                print("WARNING GCS_BUCKET_NAME not set, skipping GCS upload")
                return None
            
            # Use Application Default Credentials
            project_id = os.getenv('GCP_PROJECT_ID', 'gcp-reporting-orchestrator')
            client = storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob_path = f"generated_code/{filename}"
            blob = bucket.blob(blob_path)
            blob.upload_from_string(content)
            
            gcs_path = f"gs://{bucket_name}/{blob_path}"
            print(f"OK Saved to GCS: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            print(f"WARNING Failed to save to GCS: {e}")
            return None


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize agent
    agent = AnalystAgent()
    
    # Test analysis request
    test_request = {
        'table': 'PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.INCREMENTALITY_ANALYSIS_DUMMY',
        'treatment': 'received_email',
        'outcome': 'converted',
        'covariates': ['age_group', 'customer_segment', 'total_purchases', 'recency_bin', 
                       'email_opens_last_90_days', 'email_clicks_last_90_days'],
        'method': 'propensity_score_matching',
        'business_question': 'What is the incremental lift in conversions from email marketing?'
    }
    
    # Generate code
    result = agent.generate_analysis_code(test_request)
    
    print("\n" + "="*70)
    print("GENERATED CODE:")
    print("="*70)
    print(result['code'])
    print("\n" + "="*70)
    print(f"Saved to: {result['gcs_path']}")
    print(f"Valid syntax: {result['is_valid']}")
