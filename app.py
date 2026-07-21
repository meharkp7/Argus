"""ARGUS Gradio Interface for Hugging Face Spaces"""

import gradio as gr
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Import ARGUS components
from backend.api.schemas import HealthResponse, AlertQueryRequest, PermitSubmissionRequest
from backend.api.main import lifespan
from backend.risk_graph.scoring import score_zone_risk
from data.simulation.engine import get_simulation_engine
from backend.rag.ingest import CorpusIngester

# Initialize
engine = None
ingester = None


def init_argus():
    """Initialize ARGUS components"""
    global engine, ingester
    
    ingester = CorpusIngester()
    doc_count = ingester.ingest_all()
    print(f"✓ Indexed {doc_count} corpus documents")
    
    engine = get_simulation_engine()
    engine.start()
    print("✓ Simulation engine started")
    
    return f"ARGUS initialized - {doc_count} documents indexed"


def get_health_status():
    """Check system health"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "engine_running": engine._running if engine else False,
        "docs_indexed": len(ingester.retriever.documents) if ingester else 0
    }


def query_alerts(zone_id: str = "", alert_type: str = "all", confidence_min: float = 0.5):
    """Query alerts from the system
    
    Args:
        zone_id: Filter by zone (or "all" for all zones)
        alert_type: Type of alert (compound_risk, sensor_anomaly, permit_violation, all)
        confidence_min: Minimum confidence threshold
    """
    if not engine:
        return {"error": "Engine not initialized"}
    
    # Simulate fetching alerts
    alerts = engine.get_recent_alerts(zone_id, alert_type, confidence_min)
    return {
        "count": len(alerts),
        "alerts": alerts,
        "query_time": datetime.now().isoformat()
    }


def submit_work_permit(work_type: str, zone_id: str, duration_hours: float, description: str):
    """Submit a work permit for approval
    
    Args:
        work_type: Type of work (hot_work, electrical, confined_space, etc.)
        zone_id: Zone where work will occur
        duration_hours: Duration of work in hours
        description: Description of work
    """
    if not engine:
        return {"error": "Engine not initialized"}
    
    permit = {
        "id": f"permit_{datetime.now().timestamp()}",
        "work_type": work_type,
        "zone_id": zone_id,
        "duration_hours": duration_hours,
        "description": description,
        "submitted_at": datetime.now().isoformat(),
        "status": "pending_review"
    }
    
    # Check for compound risks
    risks = engine.check_permit_risks(permit)
    
    return {
        "permit_id": permit["id"],
        "status": permit["status"],
        "risks_detected": risks,
        "message": "Permit submitted for review"
    }


def get_heatmap_data():
    """Get current heatmap data for visualization"""
    if not engine:
        return {"error": "Engine not initialized"}
    
    zones_data = engine.get_zone_risks()
    return {
        "zones": zones_data,
        "timestamp": datetime.now().isoformat(),
        "update_frequency": "real-time"
    }


def submit_feedback(alert_id: str, was_valid: bool, notes: str = ""):
    """Submit feedback on alert accuracy for calibration
    
    Args:
        alert_id: ID of the alert
        was_valid: Whether the alert was a true positive
        notes: Additional notes
    """
    feedback_entry = {
        "alert_id": alert_id,
        "valid": was_valid,
        "notes": notes,
        "timestamp": datetime.now().isoformat()
    }
    
    if engine:
        engine.record_feedback(feedback_entry)
    
    return {
        "status": "recorded",
        "message": f"Feedback recorded - alert marked as {'valid' if was_valid else 'false positive'}",
        "timestamp": feedback_entry["timestamp"]
    }


def search_knowledge_base(query: str):
    """Search the RAG knowledge base for relevant documents
    
    Args:
        query: Search query (regulations, incident cases, procedures, etc.)
    """
    if not ingester:
        return {"error": "Knowledge base not initialized"}
    
    results = ingester.retriever.retrieve(query, top_k=5)
    
    return {
        "query": query,
        "results": [
            {
                "title": r.get("title", "Unknown"),
                "source": r.get("source", "Unknown"),
                "relevance": r.get("relevance_score", 0),
                "excerpt": r.get("content", "")[:500]
            }
            for r in results
        ]
    }


# Build Gradio Interface
with gr.Blocks(title="ARGUS - Industrial Safety Intelligence", theme=gr.themes.Soft()) as app:
    
    gr.Markdown("# 🛡️ ARGUS — Zero-Harm Intelligence Layer")
    gr.Markdown("Industrial safety intelligence platform powered by AI reasoning over sensor data, permits, and operational context.")
    
    with gr.Tabs():
        
        # System Status Tab
        with gr.Tab("System Status"):
            gr.Markdown("### System Health & Status")
            
            status_btn = gr.Button("🔍 Check Status", variant="primary")
            status_output = gr.JSON(label="System Status")
            
            status_btn.click(get_health_status, outputs=status_output)
        
        # Alerts Tab
        with gr.Tab("Alerts & Monitoring"):
            gr.Markdown("### Query Safety Alerts")
            
            with gr.Row():
                zone_input = gr.Textbox(label="Zone ID (or 'all')", value="all")
                alert_type = gr.Dropdown(
                    choices=["all", "compound_risk", "sensor_anomaly", "permit_violation"],
                    label="Alert Type",
                    value="all"
                )
                confidence = gr.Slider(0.0, 1.0, value=0.5, label="Min Confidence")
            
            query_btn = gr.Button("📊 Query Alerts", variant="primary")
            alerts_output = gr.JSON(label="Alert Results")
            
            query_btn.click(
                query_alerts,
                inputs=[zone_input, alert_type, confidence],
                outputs=alerts_output
            )
        
        # Permits Tab
        with gr.Tab("Work Permits"):
            gr.Markdown("### Submit Work Permit Request")
            
            with gr.Row():
                work_type = gr.Dropdown(
                    choices=["hot_work", "electrical", "confined_space", "maintenance"],
                    label="Work Type"
                )
                zone_id = gr.Textbox(label="Zone ID")
            
            with gr.Row():
                duration = gr.Number(label="Duration (hours)", value=2)
                description = gr.Textbox(label="Description", lines=2)
            
            permit_btn = gr.Button("✅ Submit Permit", variant="primary")
            permit_output = gr.JSON(label="Permit Response")
            
            permit_btn.click(
                submit_work_permit,
                inputs=[work_type, zone_id, duration, description],
                outputs=permit_output
            )
        
        # Heatmap Tab
        with gr.Tab("Geospatial Risk Heatmap"):
            gr.Markdown("### Real-Time Risk Map")
            
            heatmap_btn = gr.Button("🗺️ Load Heatmap Data", variant="primary")
            heatmap_output = gr.JSON(label="Zone Risk Data")
            
            heatmap_btn.click(get_heatmap_data, outputs=heatmap_output)
        
        # Knowledge Base Tab
        with gr.Tab("Knowledge Base"):
            gr.Markdown("### Search Regulations & Incident Cases")
            
            search_query = gr.Textbox(
                label="Search Query",
                placeholder="e.g., 'hot work permits', 'H2S exposure', 'confined space procedures'"
            )
            
            search_btn = gr.Button("🔎 Search", variant="primary")
            search_output = gr.JSON(label="Search Results")
            
            search_btn.click(search_knowledge_base, inputs=search_query, outputs=search_output)
        
        # Feedback Tab
        with gr.Tab("Alert Feedback"):
            gr.Markdown("### Calibrate Alert Accuracy")
            
            with gr.Row():
                alert_id_input = gr.Textbox(label="Alert ID")
                was_valid = gr.Checkbox(label="Alert was valid?", value=True)
            
            notes_input = gr.Textbox(label="Notes", lines=3)
            
            feedback_btn = gr.Button("💬 Submit Feedback", variant="primary")
            feedback_output = gr.JSON(label="Feedback Recorded")
            
            feedback_btn.click(
                submit_feedback,
                inputs=[alert_id_input, was_valid, notes_input],
                outputs=feedback_output
            )
    
    # Initialize on load
    gr.Markdown("---")
    init_btn = gr.Button("🚀 Initialize ARGUS", variant="stop", scale=2)
    init_output = gr.Textbox(label="Initialization Status")
    
    init_btn.click(init_argus, outputs=init_output)
    
    # Footer
    gr.Markdown("""
    ---
    **ARGUS** is an industrial safety intelligence platform designed for zero-harm operations.
    - 🔗 Backend: FastAPI + Agents
    - 🧠 Reasoning: Causal Risk Graph
    - 📚 Knowledge: RAG over regulations & incident cases
    - 🎯 Purpose: Real-time hazard detection & explainable alerts
    """)


if __name__ == "__main__":
    app.launch(share=True)
