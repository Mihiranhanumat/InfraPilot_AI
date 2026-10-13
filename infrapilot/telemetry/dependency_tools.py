"""
Service Dependency Graph analysis tools for InfraPilot AI.
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
import networkx as nx

def build_dependency_graph(services_df: pd.DataFrame) -> nx.DiGraph:
    """
    Construct directed dependency graph.
    Edge direction definition:
    (service -> depends_on), meaning caller points to upstream dependency.
    Example: frontend -> order_api -> database.
    Therefore:
    - An upstream dependency is reached following forward edges.
    - A downstream affected service is reached following reverse edges.
    """
    G = nx.DiGraph()
    for _, row in services_df.iterrows():
        caller = str(row["service"]).strip()
        dep = str(row["depends_on"]).strip()
        criticality = str(row.get("criticality", "medium")).strip()
        G.add_edge(caller, dep, criticality=criticality)
    return G

def get_service_dependencies(services_df: pd.DataFrame, service: str = None) -> List[Dict[str, Any]]:
    """List dependencies with criticality."""
    df = services_df.copy()
    if service:
        df = df[df["service"] == service]
    return df.to_dict(orient="records")

def get_upstream_services(services_df: pd.DataFrame, target_service: str) -> List[str]:
    """
    Return all upstream dependencies that target_service relies on (direct and transitive).
    If target_service depends on B, then B is upstream.
    """
    G = build_dependency_graph(services_df)
    if target_service not in G:
        return []
    # In graph where caller -> dep, descendants(G, target) are upstream dependencies
    return list(nx.descendants(G, target_service))

def get_downstream_impact(services_df: pd.DataFrame, failing_service: str) -> List[str]:
    """
    Return all downstream callers that may be impacted if failing_service degrades.
    In graph where caller -> dep, ancestors(G, failing_service) are downstream callers.
    """
    G = build_dependency_graph(services_df)
    if failing_service not in G:
        return []
    return list(nx.ancestors(G, failing_service))

def check_path_exists(
    services_df: pd.DataFrame,
    candidate_upstream: str,
    affected_downstream: str
) -> Tuple[bool, List[str]]:
    """
    Check if candidate_upstream can topologically cause failure in affected_downstream.
    Path is from affected_downstream -> candidate_upstream in call direction.
    """
    G = build_dependency_graph(services_df)
    if candidate_upstream not in G or affected_downstream not in G:
        return False, []
    if nx.has_path(G, affected_downstream, candidate_upstream):
        path = nx.shortest_path(G, affected_downstream, candidate_upstream)
        return True, path
    return False, []
