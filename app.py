"""
InfraPilot AI - Multi-Agent Cloud Failure Investigator
Interactive Streamlit Dashboard
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime

from infrapilot.scenario_loader import loader
from infrapilot.orchestrator import IncidentOrchestrator
from infrapilot.visualization.charts import (
    plot_incident_overview,
    plot_metric_series,
    plot_heuristic_breakdown,
)
from infrapilot.visualization.service_graph import plot_service_dependency_graph
from infrapilot.safety.policy import SAFETY_DISCLAIMER

# Page configuration
st.set_page_config(
    page_title="InfraPilot AI — Cloud Incident Investigator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern SRE dashboard aesthetic
st.markdown("""
<style>
    /* Dark glassmorphic theme styling */
    .stApp {
        background: linear-gradient(135deg, #090d16 0%, #0f172a 100%);
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        backdrop-filter: blur(8px);
    }
    .badge-critical {
        background-color: #ef4444;
        color: white;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .badge-high {
        background-color: #f97316;
        color: white;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-medium {
        background-color: #eab308;
        color: #0f172a;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-pass {
        background-color: #10b981;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 600;
    }
    .badge-escalate {
        background-color: #f59e0b;
        color: #0f172a;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
    }
    .evidence-tag {
        background: rgba(56, 189, 248, 0.15);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
        padding: 2px 7px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.8rem;
        margin-right: 4px;
        display: inline-block;
        margin-bottom: 4px;
    }
    .agent-header {
        font-size: 1.05rem;
        font-weight: 600;
        color: #38bdf8;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 10px 18px;
        background-color: rgba(30, 41, 59, 0.5);
        color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(56, 189, 248, 0.2) !important;
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8 !important;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "selected_incident_id" not in st.session_state:
    st.session_state.selected_incident_id = "INC-1001"
if "investigation_state" not in st.session_state:
    st.session_state.investigation_state = None
if "incident_injected" not in st.session_state:
    st.session_state.incident_injected = True

scenarios_list = loader.list_scenarios()
scenario_map = {s["incident_id"]: s for s in scenarios_list}

# Load cached data
@st.cache_data
def get_telemetry_dfs():
    return (
        loader.load_metrics(),
        loader.load_logs(),
        loader.load_services(),
        loader.load_events()
    )

metrics_df, logs_df, services_df, events_df = get_telemetry_dfs()

# ================= SIDEBAR =================
with st.sidebar:
    st.markdown("### ⚡ InfraPilot AI")
    st.markdown("<small style='color: #94a3b8;'>Multi-Agent Cloud Failure Investigator</small>", unsafe_allow_html=True)
    st.divider()

    st.markdown("#### Select Incident Scenario")
    scenario_options = [
        f"{s['incident_id']} — {s['title'][:26]}..." for s in scenarios_list
    ]
    selected_option_idx = 0
    for idx, s in enumerate(scenarios_list):
        if s["incident_id"] == st.session_state.selected_incident_id:
            selected_option_idx = idx
            break

    selected_choice = st.selectbox(
        "Available Scenarios",
        scenario_options,
        index=selected_option_idx
    )
    current_inc_id = selected_choice.split(" ")[0]
    if current_inc_id != st.session_state.selected_incident_id:
        st.session_state.selected_incident_id = current_inc_id
        st.session_state.investigation_state = None
        st.session_state.incident_injected = True

    current_scenario = scenario_map[st.session_state.selected_incident_id]

    # Scenario metadata box
    sev = current_scenario["severity"]
    badge_class = "badge-critical" if sev == "CRITICAL" else ("badge-high" if sev == "HIGH" else "badge-medium")
    st.markdown(f"""
    <div class="metric-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <b style="color:#e2e8f0;">{current_scenario['incident_id']}</b>
            <span class="{badge_class}">{sev}</span>
        </div>
        <div style="font-size:0.85rem; color:#cbd5e1; margin-bottom:8px;">
            {current_scenario['title']}
        </div>
        <div style="font-size:0.75rem; color:#94a3b8;">
            <b>Affected:</b> {', '.join(current_scenario['affected_services'])}<br>
            <b>Window:</b> {current_scenario['incident_window'][0].split('T')[1]} - {current_scenario['incident_window'][1].split('T')[1]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("⚡ Inject Incident", use_container_width=True):
            st.session_state.incident_injected = True
            st.session_state.investigation_state = None
            st.rerun()

    with col_btn2:
        if st.button("🔄 Reset Demo", use_container_width=True):
            st.session_state.investigation_state = None
            st.session_state.incident_injected = True
            st.rerun()

    st.markdown("---")
    
    # Run investigation trigger
    investigate_btn = st.button("🔍 Run Multi-Agent Investigation", type="primary", use_container_width=True)
    if investigate_btn:
        with st.spinner("Coordinating specialized agents..."):
            orch = IncidentOrchestrator(metrics_df, logs_df, services_df, events_df)
            st.session_state.investigation_state = orch.investigate(st.session_state.selected_incident_id)
        st.rerun()

    # Status indicator
    st.markdown("#### Investigation Status")
    inv_state = st.session_state.investigation_state
    if inv_state is None:
        st.info("Incident loaded. Ready for agent investigation.")
    else:
        if inv_state.status == "Validated hypothesis":
            st.markdown(f"<span class='badge-pass'>✔ VALIDATED HYPOTHESIS</span>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span class='badge-escalate'>⚠ NEEDS HUMAN REVIEW</span>", unsafe_allow_html=True)
        st.caption(f"Retries used: {inv_state.retry_count} / 1 | Evidence IDs registered: {len(inv_state.evidence_store)}")

    st.divider()
    st.warning(f"🛡️ **Safety Guardrail:**\n{SAFETY_DISCLAIMER}")

# ================= MAIN CONTENT =================
st.title("InfraPilot AI — Incident Response Console")
st.caption("Deterministic Multi-Agent Investigation Pipeline with Evidence Grounding & Bounded Retries")

inv_state = st.session_state.investigation_state
curr_meta = scenario_map[st.session_state.selected_incident_id]

# Incident Banner
sev_color = "#ef4444" if curr_meta["severity"] == "CRITICAL" else ("#f97316" if curr_meta["severity"] == "HIGH" else "#eab308")
st.markdown(f"""
<div style="border-left: 4px solid {sev_color}; background: rgba(30, 41, 59, 0.4); padding: 12px 18px; border-radius: 4px; margin-bottom: 20px;">
    <div style="font-size: 1.1rem; font-weight: 600; color: #f8fafc;">
        {curr_meta['incident_id']} — {curr_meta['title']}
    </div>
    <div style="font-size: 0.9rem; color: #94a3b8; margin-top: 4px;">
        <b>Symptom Summary:</b> {curr_meta['incident_summary']}
    </div>
</div>
""", unsafe_allow_html=True)

# Four Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Tab 1: Incident Overview",
    "🤖 Tab 2: Agent Activity Trace",
    "🎯 Tab 3: Root Cause & Topology",
    "📋 Tab 4: Recovery & Report Export"
])

# ================= TAB 1: INCIDENT OVERVIEW =================
with tab1:
    st.subheader("Telemetry Trends & Anomaly Timeline")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Reported Severity", curr_meta["severity"])
    with col_m2:
        st.metric("Symptom Services", len(curr_meta["affected_services"]), ", ".join(curr_meta["affected_services"]))
    with col_m3:
        st.metric("Baseline Window", f"{curr_meta['baseline_window'][0].split('T')[1]} - {curr_meta['baseline_window'][1].split('T')[1]}")
    with col_m4:
        st.metric("Incident Window", f"{curr_meta['incident_window'][0].split('T')[1]} - {curr_meta['incident_window'][1].split('T')[1]}")

    st.markdown("#### Primary Service Metrics (Latency & Error Rate)")
    fig_overview = plot_incident_overview(
        metrics_df,
        curr_meta["incident_id"],
        tuple(curr_meta["incident_window"])
    )
    st.plotly_chart(fig_overview, use_container_width=True)

    # Detailed metric tabs
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("##### Resource Utilization (CPU %)")
        fig_cpu = plot_metric_series(
            metrics_df, curr_meta["incident_id"], "cpu_pct",
            tuple(curr_meta["incident_window"])
        )
        st.plotly_chart(fig_cpu, use_container_width=True)
    with col_g2:
        if curr_meta["incident_id"] in ["INC-1001", "INC-1004"]:
            st.markdown("##### Database Connection Pool (%)")
            fig_db = plot_metric_series(
                metrics_df, curr_meta["incident_id"], "db_connections_pct",
                tuple(curr_meta["incident_window"])
            )
            st.plotly_chart(fig_db, use_container_width=True)
        else:
            st.markdown("##### Cache Hit Rate (%)")
            fig_cache = plot_metric_series(
                metrics_df, curr_meta["incident_id"], "cache_hit_rate_pct",
                tuple(curr_meta["incident_window"])
            )
            st.plotly_chart(fig_cache, use_container_width=True)

    st.markdown("#### Operational Events & Alerts Logged")
    inc_events = events_df[events_df["incident_id"] == curr_meta["incident_id"]]
    if not inc_events.empty:
        st.dataframe(
            inc_events[["timestamp", "service", "event_type", "description"]].rename(columns={
                "timestamp": "Timestamp", "service": "Service", "event_type": "Event Type", "description": "Description"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No operational events logged for this scenario.")

# ================= TAB 2: AGENT ACTIVITY TRACE =================
with tab2:
    st.subheader("Multi-Agent Execution Pipeline & Tool Calls")

    if inv_state is None:
        st.warning("Click **'Run Multi-Agent Investigation'** in the sidebar to execute the pipeline.")
    else:
        st.markdown(f"""
        <div style="background: rgba(30, 41, 59, 0.4); padding: 10px 16px; border-radius: 6px; margin-bottom: 16px;">
            <b>Investigation Trajectory:</b> {len(inv_state.agent_traces)} agent steps recorded | 
            <b>Total Retries:</b> {inv_state.retry_count} / 1 | 
            <b>Evidence Items Registered:</b> {len(inv_state.evidence_store)}
        </div>
        """, unsafe_allow_html=True)

        for idx, trace in enumerate(inv_state.agent_traces, start=1):
            with st.expander(f"Step {idx}: {trace.agent_name} ({trace.duration_ms:.1f}ms)", expanded=(idx in [1, 5, 7])):
                col_t1, col_t2 = st.columns([3, 1])
                with col_t1:
                    st.markdown(f"<span class='agent-header'>{trace.agent_name}</span> — <i>{trace.role_description}</i>", unsafe_allow_html=True)
                    st.write(f"**Findings Summary:** {trace.findings_summary}")
                    st.write(f"**Key Decision:** `{trace.decisions}`")
                with col_t2:
                    st.caption(f"Executed at {trace.timestamp}")
                    if trace.evidence_ids_generated:
                        st.markdown("**Evidence IDs:**")
                        tags_html = "".join([f"<span class='evidence-tag'>{ev}</span>" for ev in trace.evidence_ids_generated])
                        st.markdown(tags_html, unsafe_allow_html=True)

                if trace.tools_called:
                    st.markdown("**Real Local Tool Functions Executed:**")
                    for tc in trace.tools_called:
                        st.code(f"tool: {tc['tool']}\ninputs: {json.dumps(tc['inputs'])}\noutput: {tc['output']}", language="yaml")

# ================= TAB 3: ROOT CAUSE & SERVICE TOPOLOGY =================
with tab3:
    st.subheader("Root Cause Hypotheses & Service Topology")

    if inv_state is None:
        st.warning("Run the investigation to inspect root cause hypotheses and service topology.")
    else:
        col_hyp, col_graph = st.columns([1, 1])

        with col_hyp:
            st.markdown("#### Ranked Hypotheses")
            for h in inv_state.hypotheses:
                border_color = "#c084fc" if h.rank == 1 else "#64748b"
                st.markdown(f"""
                <div style="border: 1px solid {border_color}; background: rgba(30, 41, 59, 0.5); padding: 14px; border-radius: 8px; margin-bottom: 14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="color:#e2e8f0; font-size:1.05rem;">Rank #{h.rank}: {h.candidate_service.upper()}</b>
                        <span style="background:#3b82f6; color:white; font-weight:700; padding:2px 8px; border-radius:4px; font-size:0.85rem;">
                            Score: {h.heuristic_score * 100:.0f}%
                        </span>
                    </div>
                    <div style="color:#f1f5f9; font-weight:500; margin-top:6px;">
                        {h.claim}
                    </div>
                    <div style="color:#94a3b8; font-size:0.85rem; margin-top:8px;">
                        {h.reasoning}
                    </div>
                    <div style="margin-top:10px;">
                        <small style="color:#cbd5e1;"><b>Supporting Evidence:</b></small><br>
                        {''.join([f"<span class='evidence-tag'>{e}</span>" for e in h.supporting_evidence_ids])}
                    </div>
                    {f"<div style='margin-top:6px;'><small style='color:#fca5a5;'><b>Contradicting / Missing:</b></small><br>" + ''.join([f"<span class='evidence-tag' style='color:#f87171; border-color:#f87171;'>{e}</span>" for e in h.contradicting_evidence_ids]) + "</div>" if h.contradicting_evidence_ids else ""}
                </div>
                """, unsafe_allow_html=True)

            if inv_state.leading_hypothesis:
                st.markdown("##### Leading Heuristic Score Breakdown")
                fig_breakdown = plot_heuristic_breakdown(inv_state.leading_hypothesis.score_breakdown)
                st.plotly_chart(fig_breakdown, use_container_width=True)

        with col_graph:
            st.markdown("#### Service Dependency Topology")
            culprit = inv_state.leading_hypothesis.candidate_service if inv_state.leading_hypothesis and inv_state.validation and inv_state.validation.passed else None
            fig_graph = plot_service_dependency_graph(
                services_df,
                curr_meta["affected_services"],
                culprit_service=culprit
            )
            st.plotly_chart(fig_graph, use_container_width=True)

            # Critic validation card
            st.markdown("#### Critic & Validator Verdict")
            val = inv_state.validation
            verdict_badge = "<span class='badge-pass'>PASS</span>" if val.decision == "PASS" else ("<span class='badge-escalate'>NEEDS HUMAN REVIEW</span>" if val.decision == "HUMAN_REVIEW" else "<span class='badge-high'>REINVESTIGATE</span>")
            st.markdown(f"""
            <div class="metric-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <b>Critic Decision:</b>
                    {verdict_badge}
                </div>
                <div style="font-size:0.85rem; color:#cbd5e1;">
                    <ul>
                        {''.join([f"<li>{note}</li>" for note in val.critique_notes])}
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Read-only Diagnostics Checklist
            st.markdown("#### Read-Only Diagnostic Battery")
            for d in inv_state.diagnostics:
                icon = "🟢" if d.passed else "🔴"
                st.markdown(f"{icon} **{d.test_name}:** {d.details}")

# ================= TAB 4: RECOVERY & REPORT EXPORT =================
with tab4:
    st.subheader("Safe Recovery Plan & Formal Report Export")

    if inv_state is None:
        st.warning("Run the investigation to generate recommended next steps and report.")
    else:
        st.markdown("""
        > 🔒 **SAFETY POLICY NOTICE:** All remediation steps are strictly non-executing recommendations (`RECOMMENDATION_ONLY`).
        > No real infrastructure mutations have been executed. An authorized engineer must review and approve all operational changes.
        """)

        st.markdown("#### Recommended Recovery Procedure")
        for rec in inv_state.recovery_plan:
            risk_badge = "badge-critical" if rec.risk_level == "HIGH" else ("badge-high" if rec.risk_level == "MEDIUM" else "badge-pass")
            st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(148, 163, 184, 0.2); padding: 14px; border-radius: 8px; margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <b style="color:#f8fafc;">Step {rec.step_number}: {rec.action}</b>
                    <span class="{risk_badge}">RISK: {rec.risk_level}</span>
                </div>
                <div style="font-size:0.85rem; color:#cbd5e1; margin-top:6px;">
                    <b>Target Service:</b> <code>{rec.target_service}</code> | <b>Category:</b> {rec.category} | <b>Reversible:</b> {'Yes' if rec.is_reversible else 'No'}
                </div>
                <div style="font-size:0.85rem; color:#94a3b8; margin-top:4px;">
                    <b>Rationale:</b> {rec.rationale}
                </div>
                <div style="font-size:0.85rem; color:#38bdf8; margin-top:4px;">
                    <b>Post-Verification Check:</b> {rec.post_verification_check}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("#### Export Formal Investigation Report")

        col_rep1, col_rep2 = st.columns(2)
        report_agent = inv_state.report
        rep_md = report_agent and inv_state.report and inv_state.report.limitations_disclaimer
        # Generate report text using ReportingAgent
        from infrapilot.agents.reporting import ReportingAgent
        reporter = ReportingAgent()
        md_text = reporter.generate_markdown(inv_state.report)
        json_text = reporter.generate_json(inv_state.report)

        with col_rep1:
            st.download_button(
                label="📥 Download Markdown Report (.md)",
                data=md_text,
                file_name=f"{inv_state.incident_id}_investigation_report.md",
                mime="text/markdown",
                use_container_width=True
            )
        with col_rep2:
            st.download_button(
                label="📥 Download JSON Report (.json)",
                data=json_text,
                file_name=f"{inv_state.incident_id}_investigation_report.json",
                mime="application/json",
                use_container_width=True
            )

        with st.expander("📄 View Full Markdown Report Preview", expanded=False):
            st.markdown(md_text)
