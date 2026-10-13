"""
Interactive Plotly charts for InfraPilot AI.
"""
from typing import Optional, List, Tuple
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SERVICE_COLORS = {
    "frontend": "#38bdf8",       # Sky blue
    "order_api": "#f43f5e",       # Rose / Coral
    "database": "#a855f7",        # Purple
    "payment_service": "#10b981",  # Emerald green
    "inventory_service": "#f59e0b",# Amber
    "cache": "#06b6d4"           # Cyan
}

def plot_metric_series(
    metrics_df: pd.DataFrame,
    incident_id: str,
    metric_name: str,
    incident_window: Tuple[str, str],
    title: Optional[str] = None
) -> go.Figure:
    """Plot multi-service time-series for a specific metric."""
    sub_df = metrics_df[(metrics_df["incident_id"] == incident_id) & (metrics_df["metric_name"] == metric_name)].copy()
    if sub_df.empty:
        fig = go.Figure()
        fig.update_layout(
            template="plotly_dark",
            title=f"No data available for {metric_name}",
            paper_bgcolor="rgba(15,23,42,0)",
            plot_bgcolor="rgba(15,23,42,0.3)"
        )
        return fig

    sub_df = sub_df.sort_values("timestamp")
    unit = sub_df["unit"].iloc[0] if not sub_df.empty else ""

    fig = go.Figure()

    services = sub_df["service"].unique()
    for svc in services:
        svc_df = sub_df[sub_df["service"] == svc]
        color = SERVICE_COLORS.get(svc, "#94a3b8")
        fig.add_trace(go.Scatter(
            x=svc_df["timestamp"],
            y=svc_df["value"],
            mode="lines+markers",
            name=svc.replace("_", " ").title(),
            line=dict(color=color, width=2.5),
            marker=dict(size=4),
            hovertemplate=f"<b>{svc}</b><br>Time: %{{x}}<br>{metric_name}: %{{y:.2f}} {unit}<extra></extra>"
        ))

    # Add incident onset marker line
    incident_start = pd.to_datetime(incident_window[0])
    fig.add_vline(
        x=incident_start,
        line_width=2,
        line_dash="dash",
        line_color="#ef4444",
        annotation_text="Incident Onset",
        annotation_position="top left",
        annotation_font=dict(color="#f87171", size=11)
    )

    chart_title = title or f"{metric_name.replace('_', ' ').upper()} ({unit})"
    fig.update_layout(
        title=dict(text=chart_title, font=dict(size=14, color="#f1f5f9")),
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.4)",
        plot_bgcolor="rgba(30, 41, 59, 0.4)",
        hovermode="x unified",
        margin=dict(l=40, r=40, t=50, b=40),
        xaxis=dict(gridcolor="rgba(148, 163, 184, 0.1)", title="Timestamp"),
        yaxis=dict(gridcolor="rgba(148, 163, 184, 0.1)", title=unit),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def plot_incident_overview(
    metrics_df: pd.DataFrame,
    incident_id: str,
    incident_window: Tuple[str, str]
) -> go.Figure:
    """Generate side-by-side subplots for p95 latency and error rate."""
    sub_df = metrics_df[metrics_df["incident_id"] == incident_id].copy()
    if sub_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("p95 Latency (ms)", "Error Rate (%)"),
        horizontal_spacing=0.08
    )

    incident_start = pd.to_datetime(incident_window[0])

    # Left: p95 latency
    lat_df = sub_df[sub_df["metric_name"] == "p95_latency_ms"]
    for svc in lat_df["service"].unique():
        s_df = lat_df[lat_df["service"] == svc].sort_values("timestamp")
        color = SERVICE_COLORS.get(svc, "#94a3b8")
        fig.add_trace(
            go.Scatter(
                x=s_df["timestamp"], y=s_df["value"],
                mode="lines", name=svc, line=dict(color=color, width=2.2),
                legendgroup=svc
            ),
            row=1, col=1
        )

    # Right: error rate
    err_df = sub_df[sub_df["metric_name"] == "error_rate_pct"]
    for svc in err_df["service"].unique():
        s_df = err_df[err_df["service"] == svc].sort_values("timestamp")
        color = SERVICE_COLORS.get(svc, "#94a3b8")
        fig.add_trace(
            go.Scatter(
                x=s_df["timestamp"], y=s_df["value"],
                mode="lines", name=svc, line=dict(color=color, width=2.2),
                legendgroup=svc, showlegend=False
            ),
            row=1, col=2
        )

    # Add vertical onset lines to both
    fig.add_vline(x=incident_start, line_width=1.5, line_dash="dash", line_color="#ef4444", row=1, col=1)
    fig.add_vline(x=incident_start, line_width=1.5, line_dash="dash", line_color="#ef4444", row=1, col=2)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.5)",
        plot_bgcolor="rgba(30, 41, 59, 0.4)",
        height=320,
        margin=dict(l=30, r=30, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5)
    )
    return fig

def plot_heuristic_breakdown(score_breakdown: dict) -> go.Figure:
    """Radar or bar breakdown of heuristic scoring components."""
    categories = ["Metric Support", "Log Support", "Dependency Support", "Timeline Support"]
    keys = ["metric_support", "log_support", "dependency_support", "timeline_support"]
    values = [score_breakdown.get(k, 0.0) * 100 for k in keys]

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker=dict(
                color=["#38bdf8", "#a855f7", "#10b981", "#f59e0b"],
                line=dict(color="#1e293b", width=1.5)
            ),
            text=[f"{v:.0f}%" for v in values],
            textposition="auto"
        )
    ])

    fig.update_layout(
        title=dict(text="Heuristic Evidence Breakdown", font=dict(size=13, color="#e2e8f0")),
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0)",
        plot_bgcolor="rgba(30, 41, 59, 0.3)",
        yaxis=dict(range=[0, 105], title="Support (%)"),
        height=260,
        margin=dict(l=20, r=20, t=40, b=30)
    )
    return fig
