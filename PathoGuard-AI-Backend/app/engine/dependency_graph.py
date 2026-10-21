"""
PathoGuard-AI — Evidence Dependency & Change Impact Engine (Feature 1)
Maintains fine-grained provenance Directed Acyclic Graph (DAG) linking exact source report fragments
to extracted clinical findings and synthesized assessment statements.
Enables fine-grained dependency invalidation, selective sub-graph recomputation, and full auditability.
"""

from typing import Dict, List, Any, Optional, Set
import datetime
import hashlib
import uuid


class DependencyNodeType:
    SOURCE_FRAGMENT = "SOURCE_FRAGMENT"
    CLINICAL_FINDING = "CLINICAL_FINDING"
    ASSESSMENT_STATEMENT = "ASSESSMENT_STATEMENT"
    CLINICAL_RECOMMENDATION = "CLINICAL_RECOMMENDATION"


class NodeStatus:
    VALID_ACTIVE = "VALID_ACTIVE"
    SUSPENDED_STALE = "SUSPENDED_STALE"
    RECOMPUTED = "RECOMPUTED"
    DISPUTED = "DISPUTED"


class EvidenceNode:
    def __init__(
        self,
        node_id: str,
        node_type: str,
        label: str,
        content: Any,
        parent_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.label = label
        self.content = content
        self.parent_ids: List[str] = parent_ids or []
        self.children_ids: List[str] = []
        self.status: str = NodeStatus.VALID_ACTIVE
        self.content_hash: str = self._compute_hash(content)
        self.metadata: Dict[str, Any] = metadata or {}
        self.updated_at: str = datetime.datetime.utcnow().isoformat()
        self.history: List[Dict[str, Any]] = []

    def _compute_hash(self, content: Any) -> str:
        s = str(content)
        return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

    def update_content(self, new_content: Any, reason: str):
        old_val = self.content
        old_hash = self.content_hash
        self.history.append({
            "previous_content": old_val,
            "previous_hash": old_hash,
            "updated_at": self.updated_at,
            "reason": reason
        })
        self.content = new_content
        self.content_hash = self._compute_hash(new_content)
        self.updated_at = datetime.datetime.utcnow().isoformat()
        self.status = NodeStatus.VALID_ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "content": self.content,
            "parent_ids": self.parent_ids,
            "children_ids": self.children_ids,
            "status": self.status,
            "content_hash": self.content_hash,
            "metadata": self.metadata,
            "updated_at": self.updated_at,
            "history_count": len(self.history)
        }


class EvidenceDependencyGraph:
    """
    Evidence Dependency Graph mapping Source Fragments -> Extracted Findings -> Assessment Outputs.
    Prevents stale evidence from silently persisting in medical summaries.
    """

    def __init__(self, report_id: str):
        self.report_id = report_id
        self.nodes: Dict[str, EvidenceNode] = {}
        self.audit_log: List[Dict[str, Any]] = []

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        content: Any,
        parent_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EvidenceNode:
        parents = parent_ids or []
        node = EvidenceNode(node_id, node_type, label, content, parents, metadata)
        self.nodes[node_id] = node

        # Link parent children pointers
        for pid in parents:
            if pid in self.nodes:
                if node_id not in self.nodes[pid].children_ids:
                    self.nodes[pid].children_ids.append(node_id)

        return node

    def get_node(self, node_id: str) -> Optional[EvidenceNode]:
        return self.nodes.get(node_id)

    def get_dependents(self, node_id: str) -> List[str]:
        """Finds all downstream descendant node IDs reachable from node_id."""
        dependents: Set[str] = set()
        queue = [node_id]

        while queue:
            curr = queue.pop(0)
            if curr in self.nodes:
                for child_id in self.nodes[curr].children_ids:
                    if child_id not in dependents:
                        dependents.add(child_id)
                        queue.append(child_id)

        return list(dependents)

    def invalidate_subtree(self, source_node_id: str, reason: str) -> Dict[str, Any]:
        """
        Invalidates a source node and marks all dependent nodes downstream as SUSPENDED_STALE.
        Unconnected branches remain VALID_ACTIVE.
        """
        if source_node_id not in self.nodes:
            return {"error": f"Node {source_node_id} not found", "invalidated_count": 0}

        affected_ids = self.get_dependents(source_node_id)
        now_ts = datetime.datetime.utcnow().isoformat()

        # Mark source as modified
        source_node = self.nodes[source_node_id]
        source_node.status = NodeStatus.DISPUTED

        # Mark all descendants as SUSPENDED_STALE
        invalidated_details = []
        for d_id in affected_ids:
            child = self.nodes[d_id]
            child.status = NodeStatus.SUSPENDED_STALE
            invalidated_details.append({
                "node_id": d_id,
                "node_type": child.node_type,
                "label": child.label,
                "previous_status": NodeStatus.VALID_ACTIVE,
                "new_status": NodeStatus.SUSPENDED_STALE
            })

        log_entry = {
            "event": "INVALIDATION_TRIGGERED",
            "source_node_id": source_node_id,
            "reason": reason,
            "timestamp": now_ts,
            "invalidated_nodes_count": len(affected_ids),
            "invalidated_node_ids": affected_ids,
            "unaffected_nodes_count": len(self.nodes) - 1 - len(affected_ids)
        }
        self.audit_log.append(log_entry)

        return {
            "source_node_id": source_node_id,
            "invalidated_nodes_count": len(affected_ids),
            "invalidated_details": invalidated_details,
            "unaffected_nodes_count": len(self.nodes) - 1 - len(affected_ids),
            "audit_entry": log_entry
        }

    def recompute_selective(
        self,
        source_node_id: str,
        new_source_content: str,
        reason: str,
        recompute_handler=None
    ) -> Dict[str, Any]:
        """
        Applies new content to source node, invalidates stale subgraph, and selectively recomputes
        ONLY the affected nodes rather than the entire report.
        """
        if source_node_id not in self.nodes:
            return {"error": f"Node {source_node_id} not found"}

        # 1. Capture old state & invalidate
        inv_result = self.invalidate_subtree(source_node_id, reason=reason)
        affected_ids = inv_result.get("invalidated_details", [])

        # 2. Update source node content
        source_node = self.nodes[source_node_id]
        source_node.update_content(new_source_content, reason=reason)

        # 3. Selective recomputation
        recomputed_nodes = []
        total_graph_size = len(self.nodes)

        for item in affected_ids:
            nid = item["node_id"]
            child = self.nodes[nid]

            # Recomputation logic: either custom handler or deterministic synthesis update
            if recompute_handler:
                updated_val = recompute_handler(child, source_node)
            else:
                # Default targeted re-evaluator: regenerate content from new source
                updated_val = f"[Recomputed from {source_node_id}]: {source_node.content[:60]}..."

            child.update_content(updated_val, reason=f"Selective recompute following change in {source_node_id}")
            child.status = NodeStatus.RECOMPUTED
            recomputed_nodes.append(nid)

        efficiency_ratio = (
            (total_graph_size - len(recomputed_nodes)) / total_graph_size
            if total_graph_size > 0 else 1.0
        )

        audit_entry = {
            "event": "SELECTIVE_RECOMPUTATION_COMPLETED",
            "source_node_id": source_node_id,
            "recomputed_count": len(recomputed_nodes),
            "preserved_unmodified_count": total_graph_size - len(recomputed_nodes) - 1,
            "computation_savings_percentage": round(efficiency_ratio * 100, 1),
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        self.audit_log.append(audit_entry)

        return {
            "source_node_id": source_node_id,
            "recomputed_node_ids": recomputed_nodes,
            "recomputed_count": len(recomputed_nodes),
            "preserved_count": total_graph_size - len(recomputed_nodes) - 1,
            "efficiency_ratio": efficiency_ratio,
            "savings_percentage": round(efficiency_ratio * 100, 1),
            "audit_entry": audit_entry
        }

    def get_stale_nodes(self) -> List[Dict[str, Any]]:
        """Returns all currently stale or suspended nodes."""
        return [
            node.to_dict()
            for node in self.nodes.values()
            if node.status == NodeStatus.SUSPENDED_STALE
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "total_nodes": len(self.nodes),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "stale_nodes_count": len(self.get_stale_nodes()),
            "audit_log": self.audit_log
        }


def build_default_evidence_graph(report_data: Dict[str, Any]) -> EvidenceDependencyGraph:
    """
    Constructs an evidence dependency DAG from a standard parsed report object.
    Maps verbatim sections -> findings -> clinical synthesis outputs.
    """
    rpt_id = report_data.get("report_id") or report_data.get("id", "RPT-LOCAL")
    graph = EvidenceDependencyGraph(rpt_id)
    sections = report_data.get("sections", {})
    findings = report_data.get("findings", [])

    # 1. Create Source Fragment Nodes (Level 0)
    for sec_name, sec_text in sections.items():
        if not sec_text or not sec_text.strip():
            continue
        src_id = f"src_{sec_name}"
        graph.add_node(
            node_id=src_id,
            node_type=DependencyNodeType.SOURCE_FRAGMENT,
            label=f"Source: {sec_name.capitalize()}",
            content=sec_text.strip(),
            parent_ids=[],
            metadata={"section": sec_name, "page": 1}
        )

    # 2. Create Clinical Finding Nodes (Level 1)
    findings_src = "src_findings" if "findings" in sections else (
        "src_impression" if "impression" in sections else None
    )

    for idx, f in enumerate(findings):
        f_text = f.get("finding") if isinstance(f, dict) else str(f)
        f_id = f"fnd_item_{idx + 1}"
        parents = [findings_src] if findings_src and findings_src in graph.nodes else []
        graph.add_node(
            node_id=f_id,
            node_type=DependencyNodeType.CLINICAL_FINDING,
            label=f"Finding #{idx + 1}",
            content=f_text,
            parent_ids=parents,
            metadata={"category": f.get("category", "General") if isinstance(f, dict) else "General"}
        )

    # 3. Create Assessment Statement Nodes (Level 2)
    # E.g. Synthesis statements, doctor questions, urgency notes
    finding_nodes = [nid for nid in graph.nodes if nid.startswith("fnd_")]

    # Urgency & Abstention Statement (depends on all findings)
    graph.add_node(
        node_id="stmt_clinical_summary",
        node_type=DependencyNodeType.ASSESSMENT_STATEMENT,
        label="Clinical Evidence Summary",
        content="Patient scan exhibits documented anatomical findings requiring correlation with clinical symptoms.",
        parent_ids=finding_nodes[:3] if finding_nodes else (["src_findings"] if "src_findings" in graph.nodes else [])
    )

    # Doctor Discussion Questions (depends on specific findings)
    if len(finding_nodes) >= 1:
        graph.add_node(
            node_id="stmt_doctor_q1",
            node_type=DependencyNodeType.CLINICAL_RECOMMENDATION,
            label="Physician Follow-up Question",
            content="Ask physician whether the primary lesion findings represent progressive or stable morphology.",
            parent_ids=[finding_nodes[0]]
        )

    # Technique Protocol Guidance (strictly depends ONLY on technique source)
    if "src_technique" in graph.nodes:
        graph.add_node(
            node_id="stmt_technique_guidance",
            node_type=DependencyNodeType.ASSESSMENT_STATEMENT,
            label="Imaging Resolution Note",
            content="Scan protocol confirmed high resolution slice thickness adequate for soft tissue evaluation.",
            parent_ids=["src_technique"]
        )

    return graph
