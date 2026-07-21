---
title: ARGUS - Multi-Agent Safety Intelligence
emoji: 🛡️
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: "4.0.0"
python_version: "3.11"
app_file: app.py
pinned: false
---

# 🛡️ ARGUS - Multi-Agent Industrial Safety Intelligence

**Zero-Harm Intelligence Layer for Industrial Operations**

ARGUS is an AI-powered multi-agent system that fuses real-time sensor telemetry, operational permits, incident knowledge, and causal reasoning to detect and prevent compound industrial hazards before they occur.

## 🤖 Agent Architecture

Five specialized autonomous agents work together in real-time:

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Sensor Agent** | Anomaly detection | Raw sensor streams | Anomalies with confidence scores |
| **Permit Agent** | Regulatory compliance | Work permits + regulations | Compliance status + violations |
| **Correlation Agent** | Compound hazards | Multiple signals | Risk correlations |
| **Explainer Agent** | Causal reasoning | Alerts + context | Audit-ready explanations |
| **Orchestrator** | Incident response | Scenario data | Unified escalation action |

## 🎯 Key Differentiator

Most industrial safety systems catch **single sensor exceedances**. ARGUS catches **compound hazards** — the combinations that actually kill people.

**Example:** Hot work permit + rising H2S readings + shift changeover + equipment failure = **CRITICAL** (not just individual alerts)

## ✨ Features

- **Explainable AI:** Every alert has a traceable causal chain for regulatory audits
- **Real-time reasoning:** Sub-second response to compound hazard detection
- **Multi-source fusion:** SCADA, permits, weather, maintenance logs, shift rosters
- **Knowledge-grounded:** RAG over regulations (OISD, Factory Act, DGMS) + incident cases
- **Frontline-ready:** Designed for operators, not just control rooms

## 📊 Demo Tabs

1. **Initialize System** - Start agents and knowledge base
2. **Sensor Agent** - Try anomaly detection
3. **Permit Agent** - Check regulatory compliance
4. **Correlation Agent** - Find compound hazards
5. **Explainer Agent** - Get causal explanations
6. **Orchestrator** - See full incident response

## 🏗️ Architecture

```
Real-time Inputs
    ↓
[Sensor Agent] → Detects anomalies
    ↓
[Permit Agent] → Validates operations
    ↓
[Correlation Agent] → Finds compound hazards
    ↓
[Explainer Agent] → Generates causal chains
    ↓
[Orchestrator] → Routes to Safety Officer
    ↓
Action + Audit Trail
```

## 💾 Data Flow

- **Sensor Data:** Temperature, pressure, gas concentrations (H2S, CO, O₂)
- **Permits:** Hot work, electrical, confined space, excavation
- **Context:** Shift roster, weather, maintenance schedule
- **Knowledge:** Regulations (OISD GDN 117, Factory Act, DGMS), incident cases
- **Output:** Alerts, explanations, escalations

## 🔐 Compliance

- Full causal chain for every alert (audit-ready)
- Evidence sourced from multiple systems
- Confidence scores on all determinations
- Incident case references for learned patterns

## 🚀 Quick Start

1. Click **"Initialize System"** tab
2. Hit the Initialize button (loads agents + KB)
3. Try any agent tab with example data
4. See output format and reasoning

## 📚 Knowledge Sources

- **Regulations:** OISD GDN 117 (hot work), Factory Act, DGMS safety circulars
- **Incident Cases:** Vizag Steel Plant, Bhopal legacy, refinery fires, mine incidents
- **Procedures:** Confined space entry, gas testing, permit workflows

## 💡 Use Case Example

**Scenario:** Safety officer checking if hot work + maintenance can happen simultaneously

1. **Submit permit** → Permit Agent checks OISD compliance
2. **Add sensor readings** → Sensor Agent detects H2S spike
3. **Check context** → Correlation Agent finds: hot work + gas anomaly = danger
4. **Get explanation** → Explainer Agent shows causal chain + historical case match
5. **Escalate** → Orchestrator recommends STOP or MITIGATION

All in <2 seconds with full audit trail.

---

**Built for:** Indian heavy industry  
**Version:** 1.0.0  
**Contact:** ARGUS Development Team

---

Check out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference
