"""Page 4: AI summary generation and report download."""

import streamlit as st

from ad_audit.report.llm_summary import generate_summary
from ad_audit.report.html_export import export_html_report

st.set_page_config(page_title="Report", page_icon="📝", layout="wide")
st.title("📝 Audit Report")

result = st.session_state.get("audit_result")

if result is None:
    st.warning("No audit results yet. Please run an audit first.")
    st.stop()

# AI Summary
st.markdown("### AI-Powered Summary")
st.markdown(
    "Generate a natural-language summary of the audit findings using OpenAI."
)

api_key = st.text_input(
    "OpenAI API Key",
    type="password",
    help="Your key is not stored. Leave blank to skip AI summary.",
)

col1, col2 = st.columns(2)

with col1:
    if st.button("Generate AI Summary", type="primary", disabled=not api_key):
        with st.spinner("Generating summary..."):
            try:
                summary = generate_summary(result, api_key=api_key)
                st.session_state["ai_summary"] = summary
            except Exception as e:
                st.error(f"Summary generation failed: {e}")

ai_summary = st.session_state.get("ai_summary", "")

if ai_summary:
    st.markdown("---")
    st.markdown(ai_summary)

# Manual summary fallback
st.markdown("---")
st.markdown("### Key Findings")
s = result.summary_dict

findings = f"""
- **Audit Mode**: {s['mode']}
- **Reported ROAS**: {s['reported_roas']:.2f}x
- **True Incremental ROAS**: {s['true_incremental_roas']:.2f}x
- **ROAS Inflation**: {s['inflation_rate']:.1%}
- **Duplication Rate**: {s['duplication_rate']:.1%}
- **Cannibalization Score**: {s['cannibalization_score']:.1%}
"""

if result.total_matched_orders > 0:
    findings += f"""
- **Matched Orders**: {s['total_matched_orders']:,}
- **Truly Incremental Orders**: {s['truly_incremental_orders']:,}
- **Cannibalized Orders**: {s['cannibalized_orders']:,}
"""

st.markdown(findings)

# HTML Report Download
st.markdown("---")
st.markdown("### Download Report")

with col2:
    if st.button("Generate HTML Report"):
        with st.spinner("Building report..."):
            try:
                html = export_html_report(result, ai_summary=ai_summary)
                st.session_state["html_report"] = html
                st.success("Report generated!")
            except Exception as e:
                st.error(f"Report generation failed: {e}")

html_report = st.session_state.get("html_report")

if html_report:
    st.download_button(
        label="Download HTML Report",
        data=html_report,
        file_name="ad_audit_report.html",
        mime="text/html",
    )
