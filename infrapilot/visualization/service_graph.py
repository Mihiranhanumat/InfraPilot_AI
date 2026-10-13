"""
Service Dependency Graph visualizer using NetworkX and Plotly.
"""
from typing import List, Optional, Dict
import pandas as pd
import networkx as nx
import plotly.graph_objects as go
from infrapilot.telemetry.dependency_tools import build_dependency_graph

def plot_service_dependency_graph(
    services_df: pd.DataFrame,
    symptom_services: List[str],
    culprit_service: Optional[str] = None
) -> go.Figure:
    """
    Renders interactive topological graph of service dependencies with status coloring.
    Direction: Caller -> Upstream Dependency.
    """
    G = build_dependency_graph(services_df)

    # Fixed positions for clean architecture flow:
    # Top/Left: Users/Frontend -> Middle: Order API -> Right: Database, Payment, Inventory, Cache
    fixed_pos = {
        "frontend": (0.1, 0.5),
        "order_api": (0.45, 0.5),
        "cache": (0.85, 0.8),
        "database": (0.85, 0.5),
        "payment_service": (0.85, 0.2),
        "inventory_service": (0.55, 0.15),
    }

    pos = {}
    for node in G.nodes():
        pos[node] = fixed_pos.get(node, nx.spring_layout(G).get(node, (0.5, 0.5)))

    # Edges
    edge_x = []
    edge_y = []
    edge_annotations = []

    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

        # Arrow annotation towards upstream dependency
        edge_annotations.append(dict(
            ax=x0, ay=y0,
            x=x1, y=y1,
            xref='x', yref='y', axref='x', ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=1.5,
            arrowcolor="rgba(148, 163, 184, 0.55)"
        ))

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1.5, color="rgba(148, 163, 184, 0.4)"),
        hoverinfo='none',
        mode='lines'
    )

    # Nodes
    node_x = []
    node_y = []
    node_text = []
    node_colors = []
    node_border_colors = []
    node_sizes = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        # Health state determination
        if culprit_service and node == culprit_service:
            status = "Identified Root Cause"
            fill_color = "#c084fc"   # Purple
            border_color = "#f3e8ff"
            size = 38
        elif node in symptom_services:
            status = "Reported Symptom"
            fill_color = "#ef4444"   # Red
            border_color = "#fee2e2"
            size = 32
        else:
            status = "Operational / Baseline"
            fill_color = "#10b981"   # Emerald
            border_color = "#a7f3d0"
            size = 28

        node_colors.append(fill_color)
        node_border_colors.append(border_color)
        node_sizes.append(size)
        node_text.append(f"<b>{node.upper()}</b><br>Role: {status}<br>In-degree: {G.in_degree(node)} | Out-degree: {G.out_degree(node)}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[n.replace("_", " ").title() for n in G.nodes()],
        textposition="top center",
        textfont=dict(size=12, color="#f8fafc", family="sans-serif"),
        hovertext=node_text,
        marker=dict(
            color=node_colors,
            size=node_sizes,
            line=dict(width=2.5, color=node_border_colors),
            opacity=0.95
        )
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=dict(
            text="Service Call Dependency Topology (Caller → Upstream)",
            font=dict(size=14, color="#f1f5f9")
        ),
        showlegend=False,
        hovermode='closest',
        margin=dict(b=20, l=20, r=20, t=50),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.4)",
        plot_bgcolor="rgba(30, 41, 59, 0.3)",
        height=340,
        annotations=edge_annotations
    )
    return fig
