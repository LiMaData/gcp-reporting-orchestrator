"""
Agent 4 – Report Generator (Gemini 2.5 Flash)
Generates persona‑specific HTML reports (and optionally Google Slides) from the insights produced by Agent 3.
"""

import os
import json
import logging
from datetime import datetime

# Gemini client
import google.generativeai as genai


class ReportGeneratorAgent:
    """Create a marketing‑focused report for a given persona.

    * Input – `insights` (dict or JSON string) from the InterpreterAgent.
    * Persona – one of ``CMO``, ``Marketing Ops`` or ``Data Team``.
    * Output – HTML string (ready to be embedded in a Slides deck) and a
      JSON payload that can be stored in GCS.
    """

    def __init__(self):
        # Load API key – fall back to a mock implementation if missing.
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            logging.info("GOOGLE_API_KEY not set – ReportGeneratorAgent will use a mock report.")
            self.use_mock = True
        else:
            self.use_mock = False
            genai.configure(api_key=self.api_key)
            # Use the most capable flash model available.
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]
            self.model = genai.GenerativeModel("gemini-2.5-flash", safety_settings=safety_settings)

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def generate_report(self, insights, persona="CMO", output_format="html"):
        """Return a dict with ``html``, ``metadata``, and optional ``gcs_path`` keys.

        Args:
            insights (dict | str): Output from InterpreterAgent.
            persona (str): Target audience – ``CMO``, ``Marketing Ops`` or ``Data Team``.
            output_format (str): 'html' or 'pdf'. If 'pdf', saves to GCS.
        """
        if isinstance(insights, str):
            try:
                insights = json.loads(insights)
            except json.JSONDecodeError:
                logging.warning("Insights string could not be parsed – passing raw string to model.")
        
        if self.use_mock:
            result = self._mock_report(insights, persona)
        else:
            result = self._gemini_report(insights, persona)
            
        if output_format == 'pdf':
            pdf_bytes = self._convert_to_pdf(result['html'])
            if pdf_bytes:
                # Save as latest (overwrite)
                filename = f"latest_{persona.lower().replace(' ', '_')}_report.pdf"
                gcs_path = self._save_to_gcs(pdf_bytes, filename, content_type='application/pdf')
                result['gcs_path'] = gcs_path
                
        return result

    def generate_all_persona_reports(self, insights, output_format='pdf'):
        """Generate reports for all three personas (CMO, Marketing Ops, Data Team).
        
        Args:
            insights (dict | str): Output from InterpreterAgent.
            output_format (str): 'html' or 'pdf'. If 'pdf', saves to GCS.
            
        Returns:
            dict: Results for each persona with keys 'cmo', 'marketing_ops', 'data_team'
        """
        personas = {
            'cmo': 'CMO',
            'marketing_ops': 'Marketing Ops',
            'data_team': 'Data Team'
        }
        
        results = {}
        
        for key, persona in personas.items():
            logging.info(f"Generating {persona} report...")
            try:
                result = self.generate_report(insights, persona=persona, output_format=output_format)
                results[key] = result
                
                if output_format == 'pdf' and 'gcs_path' in result:
                    logging.info(f"✓ {persona} report saved to: {result['gcs_path']}")
                    
            except Exception as e:
                logging.error(f"Failed to generate {persona} report: {e}")
                results[key] = {'error': str(e)}
                
        return results

    def _convert_to_pdf(self, html_content):
        """Convert HTML to PDF bytes using xhtml2pdf."""
        try:
            from xhtml2pdf import pisa
            from io import BytesIO
            
            pdf_buffer = BytesIO()
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
            
            if pisa_status.err:
                logging.error("PDF generation failed")
                return None
            return pdf_buffer.getvalue()
            
        except ImportError:
            logging.warning("xhtml2pdf not installed. Cannot generate PDF.")
            return None
        except Exception as e:
            logging.error(f"PDF generation error: {e}")
            return None

    def _save_to_gcs(self, content, filename, content_type='text/html'):
        """Save content to GCS bucket in reports/ subfolder."""
        try:
            from google.cloud import storage
            
            bucket_name = os.getenv('GCS_BUCKET_NAME')
            project_id = os.getenv('GCP_PROJECT_ID', 'gcp-reporting-orchestrator')
            
            if not bucket_name:
                logging.warning("GCS_BUCKET_NAME not set, skipping upload")
                return None
                
            client = storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob_path = f"reports/{filename}"
            blob = bucket.blob(blob_path)
            
            blob.upload_from_string(content, content_type=content_type)
            
            gcs_path = f"gs://{bucket_name}/{blob_path}"
            logging.info(f"Saved report to GCS: {gcs_path}")
            return gcs_path
            
        except Exception as e:
            logging.error(f"Failed to save to GCS: {e}")
            return None

    # ---------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------
    def _mock_report(self, insights, persona):
        """Return a static HTML report – useful for local dev / CI."""
        html = f"""
        <div class='report'>
            <h1>{persona} Report – Mock</h1>
            <p><strong>Summary:</strong> {insights.get('summary', 'No summary provided.')}</p>
            <p><strong>Key Findings:</strong> {'; '.join(insights.get('key_findings', []))}</p>
            <p><strong>Recommendation:</strong> {insights.get('recommendation', 'N/A')}</p>
            <p><em>Generated on {datetime.utcnow().isoformat()}Z (mock)</em></p>
        </div>
        """
        metadata = {
            "persona": persona,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mock": True,
        }
        return {"html": html, "metadata": metadata}

    def _gemini_report(self, insights, persona):
        """Ask Gemini to format the insights as a polished HTML snippet."""
        # Convert insights dict to a pretty JSON string for the prompt.
        insights_str = json.dumps(insights, indent=2)
        
        # Define persona-specific guidance
        persona_guidance = {
            "CMO": """
            - Focus on strategic impact, ROI, and business outcomes
            - Use executive language and highlight bottom-line impact
            - Emphasize competitive advantage and market positioning
            - Keep technical details minimal
            - Include clear recommendations for scaling or stopping
            """,
            "Marketing Ops": """
            - Focus on implementation details, campaign efficiency, and operational metrics
            - Include specific numbers on campaign performance and conversion rates
            - Discuss execution challenges and optimization opportunities
            - Provide actionable next steps for campaign management
            - Balance strategic context with tactical recommendations
            """,
            "Data Team": """
            - Focus on methodology, statistical rigor, and data quality
            - Include technical details about the analysis approach
            - Discuss assumptions, limitations, and confidence levels
            - Mention specific statistical tests, p-values, and confidence intervals
            - Provide data quality assessments and validation checks
            """
        }
        
        guidance = persona_guidance.get(persona, persona_guidance["CMO"])
        
        prompt = f"""
        You are a senior marketing communications specialist creating a report for a specific audience.
        
        TARGET PERSONA: {persona}
        
        Create a concise, persona-specific HTML report (no <html>/<head>/<body> tags, just the inner <div> content).
        
        CRITICAL REQUIREMENTS:
        1. The report MUST begin with: <h1>{persona} Report</h1>
        2. The title must say "{persona} Report" - NOT "CMO Report" or any other persona
        3. Tailor ALL content specifically for the {persona} audience
        
        PERSONA-SPECIFIC GUIDANCE FOR {persona}:
        {guidance}
        
        STRUCTURE:
        - <h1>{persona} Report</h1>
        - <h2>Summary</h2> (2-3 sentences tailored to {persona})
        - <h2>Key Findings</h2> (bullet list with <ul>/<li>)
        - <h2>Recommendation</h2> (specific to {persona}'s needs)
        - Use simple inline styling: <strong>, <em>, <ul>/<li>
        
        INSIGHTS DATA:
        {insights_str}
        
        Remember: This is for {persona}, so tailor the language, metrics, and recommendations accordingly.
        Output ONLY the HTML content, no markdown code blocks.
        """
        try:
            response = self.model.generate_content(prompt)
            html = response.text.strip()
            
            # Remove markdown code blocks if present
            if '```html' in html:
                html = html.split('```html')[1].split('```')[0].strip()
            elif '```' in html:
                html = html.split('```')[1].split('```')[0].strip()
            
            metadata = {
                "persona": persona,
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "mock": False,
            }
            return {"html": html, "metadata": metadata}
        except Exception as e:
            logging.error(f"Gemini report generation failed: {e}")
            return self._mock_report(insights, persona)



# ---------------------------------------------------------------------
# Simple CLI test
# ---------------------------------------------------------------------
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    sample_insights = {
        "summary": "The campaign delivered a 5.4% incremental lift with high confidence.",
        "key_findings": ["Lift is positive", "Statistically significant", "Effect size modest"],
        "recommendation": "Scale the campaign while monitoring cost per acquisition.",
        "confidence_level": "High",
    }
    agent = ReportGeneratorAgent()
    result = agent.generate_report(sample_insights, persona="CMO", output_format='pdf')
    print("--- HTML REPORT ---")
    print(result["html"][:200] + "...")
    if 'gcs_path' in result:
        print(f"--- GCS PDF ---")
        print(result['gcs_path'])
