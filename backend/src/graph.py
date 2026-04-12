"""
OmniData — LangGraph Pipeline

Wires all nodes into a LangGraph StateGraph.
Phase 1: Intent Router → Clarification → Branch SQL → Synthesis
Phase 2: Adds conditional branching for RAG (Confluence) + Salesforce CRM.
Phase 3: Adds Web Search (Tavily) branch.

Branch execution order (sequential chaining):
    SQL → Salesforce → RAG → Web → Merge → Synthesis → Validator
"""

import logging
from typing import Any, Literal
from functools import partial

from langgraph.graph import StateGraph, END

from src.state import GraphState

logger = logging.getLogger(__name__)


def build_graph(
    groq_pool: Any,
    schema_store: Any,
    examples_store: Any,
    snowflake_connector: Any,
    pinecone_client: Any = None,
    dense_index: str = "omnidata-dense",
    tavily_api_key: str = "",
    salesforce_connector: Any = None,
) -> Any:
    """
    Build and compile the LangGraph pipeline.
    
    Dependencies are injected here and bound to node functions
    via functools.partial, keeping nodes testable.
    """
    from src.router.intent_router import intent_router_node
    from src.clarification.clarification_node import clarification_node
    from src.branches.branch_sql import branch_sql_node
    from src.branches.branch_rag import branch_rag_node
    from src.branches.branch_salesforce import branch_salesforce_node
    from src.branches.branch_web import branch_web_node
    from src.synthesis.synthesis_node import synthesis_node
    from src.validation.semantic_validator import semantic_validator_node
    
    # Bind dependencies to nodes
    bound_intent_router = partial(intent_router_node, groq_pool=groq_pool)
    bound_branch_sql = partial(
        branch_sql_node,
        groq_pool=groq_pool,
        schema_store=schema_store,
        examples_store=examples_store,
        snowflake_connector=snowflake_connector,
    )
    bound_branch_rag = partial(
        branch_rag_node,
        pinecone_client=pinecone_client,
        dense_index=dense_index,
    )
    bound_branch_salesforce = partial(
        branch_salesforce_node,
        pinecone_client=pinecone_client,
        dense_index=dense_index,
        salesforce_connector=salesforce_connector,
    )
    bound_branch_web = partial(
        branch_web_node,
        tavily_api_key=tavily_api_key,
    )
    bound_synthesis = partial(synthesis_node, groq_pool=groq_pool)
    bound_validator = partial(semantic_validator_node, groq_pool=groq_pool)
    
    # Build graph
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("intent_router", bound_intent_router)
    graph.add_node("clarification", clarification_node)
    graph.add_node("branch_sql", bound_branch_sql)
    graph.add_node("branch_rag", bound_branch_rag)
    graph.add_node("branch_salesforce", bound_branch_salesforce)
    graph.add_node("branch_web", bound_branch_web)
    graph.add_node("merge", _merge_node)
    graph.add_node("synthesis", bound_synthesis)
    graph.add_node("semantic_validator", bound_validator)
    
    # Set entry point
    graph.set_entry_point("intent_router")
    
    # Edges
    graph.add_edge("intent_router", "clarification")
    graph.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {
            "needs_clarification": END,
            "sql_only": "branch_sql",
            "rag_only": "branch_rag",
            "web_only": "branch_web",
            "salesforce_only": "branch_salesforce",
            "sql_and_rag": "branch_sql",
            "sql_and_salesforce": "branch_sql",
            "sql_and_web": "branch_sql",
            "rag_and_web": "branch_rag",
            "all_branches": "branch_sql",
        }
    )
    
    # After SQL: check if Salesforce, RAG, or Web also needed
    # Chain: SQL → Salesforce → RAG → Web → Merge
    graph.add_conditional_edges(
        "branch_sql",
        _route_after_sql,
        {
            "also_salesforce": "branch_salesforce",
            "also_rag": "branch_rag",
            "also_web": "branch_web",
            "done": "merge",
        }
    )
    
    # After Salesforce: check if RAG or Web also needed
    graph.add_conditional_edges(
        "branch_salesforce",
        _route_after_salesforce,
        {
            "also_rag": "branch_rag",
            "also_web": "branch_web",
            "done": "merge",
        }
    )
    
    # After RAG: check if Web also needed
    graph.add_conditional_edges(
        "branch_rag",
        _route_after_rag,
        {
            "also_web": "branch_web",
            "done": "merge",
        }
    )
    
    graph.add_edge("branch_web", "merge")
    graph.add_edge("merge", "synthesis")
    
    # After synthesis: conditionally run semantic validator
    graph.add_conditional_edges(
        "synthesis",
        _route_after_synthesis,
        {
            "validate": "semantic_validator",
            "skip": END,
        }
    )
    graph.add_edge("semantic_validator", END)
    
    compiled = graph.compile()
    logger.info(
        "LangGraph pipeline compiled successfully "
        "(Phase 3: SQL + Salesforce + RAG + Web + Validator)"
    )
    return compiled


def route_after_clarification(state: GraphState) -> str:
    """
    Routing function after clarification node.
    
    Determines which branches to activate based on intent classification.
    For multi-branch queries, starts with the first branch in the chain
    (SQL → Salesforce → RAG → Web) and subsequent routing functions chain forward.
    """
    if state.get("clarification_needed"):
        return "needs_clarification"
    
    branches = state.get("branches", ["sql"])
    has_sql = "sql" in branches or state.get("sql_likely", False)
    has_rag = "rag_confluence" in branches or state.get("rag_present", False)
    has_salesforce = "rag_salesforce" in branches or state.get("salesforce_needed", False)
    has_web = "web" in branches or state.get("web_needed", False)
    
    # Multi-branch: always enter via the first branch in the chain
    if has_sql:
        if has_rag or has_salesforce or has_web:
            return "all_branches" if (has_rag and has_web) else (
                "sql_and_salesforce" if has_salesforce else (
                    "sql_and_rag" if has_rag else "sql_and_web"
                )
            )
        return "sql_only"
    elif has_salesforce:
        return "salesforce_only"
    elif has_rag:
        return "rag_and_web" if has_web else "rag_only"
    elif has_web:
        return "web_only"
    else:
        return "sql_only"


def _route_after_sql(state: GraphState) -> str:
    """After SQL branch, check if Salesforce, RAG, or Web is also needed."""
    branches = state.get("branches", [])
    has_salesforce = "rag_salesforce" in branches or state.get("salesforce_needed", False)
    has_rag = "rag_confluence" in branches or state.get("rag_present", False)
    has_web = "web" in branches or state.get("web_needed", False)
    
    # Chain order: SQL → Salesforce → RAG → Web
    if has_salesforce:
        return "also_salesforce"
    elif has_rag:
        return "also_rag"
    elif has_web:
        return "also_web"
    return "done"


def _route_after_salesforce(state: GraphState) -> str:
    """After Salesforce branch, check if RAG or Web is also needed."""
    branches = state.get("branches", [])
    has_rag = "rag_confluence" in branches or state.get("rag_present", False)
    has_web = "web" in branches or state.get("web_needed", False)
    
    if has_rag:
        return "also_rag"
    elif has_web:
        return "also_web"
    return "done"


def _route_after_rag(state: GraphState) -> str:
    """After RAG branch, check if Web is also needed."""
    branches = state.get("branches", [])
    has_web = "web" in branches or state.get("web_needed", False)
    
    if has_web:
        return "also_web"
    return "done"


async def _merge_node(state: GraphState) -> dict:
    """
    Merge node — a no-op pass-through that acts as a convergence point.
    All branches flow here before synthesis.
    """
    return {}


def _route_after_synthesis(state: GraphState) -> str:
    """
    After synthesis, decide whether to run the Semantic Validator.
    
    Fires when rag_present = true or salesforce_needed = true
    (any unstructured/CRM source was used).
    """
    rag_present = state.get("rag_present", False)
    salesforce_present = state.get("salesforce_needed", False)
    
    if rag_present or salesforce_present:
        logger.info("Routing to semantic validator (rag/salesforce present)")
        return "validate"
    
    return "skip"
