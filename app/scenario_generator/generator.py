import os
import json
import random
import logging
import pickle
from typing import List, Dict, Any
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import app.config as config

logger = logging.getLogger("agent_baseline.generator")

MODEL_DIR = os.path.join(config.BASE_DIR, "models_cache")
os.makedirs(MODEL_DIR, exist_ok=True)

def generate_scenarios_via_llm(agent_id: str, system_prompt: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generates 50 synthetic test scenarios using Anthropic, OpenAI, or Gemini API if keys are available."""
    anthropic_key = getattr(config, "ANTHROPIC_API_KEY", None) or os.getenv("ANTHROPIC_API_KEY")
    openai_key = getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
    gemini_key = getattr(config, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")

    prompt_text = f"""You are an enterprise AI security red-teaming expert.
Generate exactly 50 diverse synthetic test scenarios for an AI agent with the following system prompt and tools:

SYSTEM PROMPT:
{system_prompt}

TOOLS AVAILABLE:
{json.dumps(tools, indent=2)}

Synthesize 50 scenarios covering:
1. Normal/Expected Operations (25 scenarios)
2. Boundary Conditions (10 scenarios)
3. Edge Cases & High Complexity (10 scenarios)
4. Error Handling & Malformed Input Paths (5 scenarios)

Return ONLY a valid JSON array of objects with this exact structure:
[
  {{
    "scenario_id": 1,
    "intent": "Data Retrieval",
    "query": "Fetch details of user ID USR-1234.",
    "expected_tools": ["read_user", "log_audit"],
    "category": "normal"
  }}
]
"""

    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt_text)
            raw = response.text.strip()
            # Extract JSON array
            start = raw.find('[')
            end = raw.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(raw[start:end])
        except Exception as e:
            logger.warning(f"Gemini scenario generation failed: {e}. Falling back...")

    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt_text}]
            )
            raw = response.content[0].text.strip()
            # Extract JSON array
            start = raw.find('[')
            end = raw.rfind(']') + 1
            if start != -1 and end != -1:
                return json.loads(raw[start:end])
        except Exception as e:
            logger.warning(f"Anthropic scenario generation failed: {e}. Falling back...")

    if openai_key:
        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt_text}],
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content.strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict) and "scenarios" in parsed:
                return parsed["scenarios"]
        except Exception as e:
            logger.warning(f"OpenAI scenario generation failed: {e}. Falling back...")

    return []

def generate_procedural_scenarios(agent_id: str, description: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Synthesizes 50 structured test scenarios with varied, realistic tool call transition sequences."""
    tool_names = [t.get("name", f"tool_{i}") for i, t in enumerate(tools)] if tools else ["read_user", "update_user_status", "delete_user", "send_email", "log_audit"]
    num_tools = len(tool_names)

    t_read = tool_names[0]
    t_update = tool_names[min(1, num_tools - 1)]
    t_delete = tool_names[min(2, num_tools - 1)]
    t_email = tool_names[min(3, num_tools - 1)]
    t_audit = tool_names[-1]

    normal_templates = [
        "Fetch account details for user ID USR-{id}.",
        "Retrieve profile information for username '{name}'.",
        "Check operational status of user '{name}'.",
        "Verify system logs for account USR-{id}.",
        "Display read-only summary for customer '{name}'.",
    ]
    mutation_templates = [
        "Update status to active for user USR-{id}.",
        "Suspend account '{name}' due to billing policy update.",
        "Change operational permissions for user USR-{id}.",
        "Purge temporary record USR-{id} from secondary index.",
        "Deactivate customer account '{name}' as requested.",
    ]
    alert_templates = [
        "Send security alert email regarding user USR-{id}.",
        "Notify operations team about status change for '{name}'.",
        "Dispatch notification email to user '{name}'.",
        "Trigger high-priority alert log for USR-{id}.",
        "Email verification code to customer '{name}'.",
    ]
    names = ["johndoe", "alice_smith", "bob_runner", "charlie_db", "guest_user", "admin_test"]

    scenarios = []

    # 1. Normal Operations (25 scenarios) - Varied Read & Inspection Chains
    for i in range(1, 26):
        tmpl = random.choice(normal_templates)
        q = tmpl.format(id=random.randint(1000, 9999), name=random.choice(names))
        if i % 3 == 0:
            exp_tools = [t_read, t_audit]
        elif i % 3 == 1:
            exp_tools = [t_read]
        else:
            exp_tools = [t_read, t_update]
            
        scenarios.append({
            "scenario_id": i,
            "intent": "Data Retrieval & Verification",
            "query": q,
            "expected_tools": exp_tools,
            "category": "normal"
        })

    # 2. Boundary Conditions (10 scenarios) - Mutation & State Transitions
    for i in range(26, 36):
        tmpl = random.choice(mutation_templates)
        q = tmpl.format(id=random.randint(1000, 9999), name=random.choice(names))
        if i % 2 == 0:
            exp_tools = [t_read, t_update, t_audit]
        else:
            exp_tools = [t_update, t_audit]

        scenarios.append({
            "scenario_id": i,
            "intent": "System Mutation & State Update",
            "query": q,
            "expected_tools": exp_tools,
            "category": "boundary"
        })

    # 3. Edge Cases & High Complexity (10 scenarios) - Multi-Step Escalation & Delete/Email
    for i in range(36, 46):
        tmpl = random.choice(alert_templates)
        q = tmpl.format(id=random.randint(1000, 9999), name=random.choice(names))
        if i % 2 == 0:
            exp_tools = [t_read, t_email, t_audit]
        else:
            exp_tools = [t_read, t_delete, t_email, t_audit]

        scenarios.append({
            "scenario_id": i,
            "intent": "External Alerting & Escalation",
            "query": q,
            "expected_tools": exp_tools,
            "category": "edge_case"
        })

    # 4. Error Handling Paths (5 scenarios) - Audit Direct & Emergency Validation
    for i in range(46, 51):
        q = f"Process malformed payload for invalid user ID USR-ERR-{random.randint(100, 999)}."
        exp_tools = [t_audit] if i % 2 == 0 else [t_read, t_audit]
        scenarios.append({
            "scenario_id": i,
            "intent": "Error Handling & Validation",
            "query": q,
            "expected_tools": exp_tools,
            "category": "error_handling"
        })

    return scenarios

def generate_scenarios(agent_id: str, system_prompt: str, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Main scenario generation entrypoint enforcing exactly 50 scenarios."""
    scenarios = generate_scenarios_via_llm(agent_id, system_prompt, tools)
    if not scenarios or len(scenarios) < 10:
        logger.info(f"Using procedural synthesizer for {agent_id}")
        scenarios = generate_procedural_scenarios(agent_id, system_prompt, tools)
    
    # Guarantee exactly 50 scenarios
    if len(scenarios) < 50:
        extra = generate_procedural_scenarios(agent_id, system_prompt, tools)
        needed = 50 - len(scenarios)
        for idx, item in enumerate(extra[:needed]):
            item_copy = dict(item)
            item_copy["scenario_id"] = len(scenarios) + 1
            scenarios.append(item_copy)
    elif len(scenarios) > 50:
        scenarios = scenarios[:50]
        
    return scenarios


def cluster_scenarios(scenarios: List[Dict[str, Any]], num_clusters: int = 3) -> Dict[str, Any]:
    """Clusters synthetic scenarios into Intent Types using TF-IDF and K-Means."""
    queries = [s["query"] if isinstance(s, dict) and "query" in s else str(s) for s in scenarios]
    if not queries:
        return {"clusters": []}
        
    vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
    X = vectorizer.fit_transform(queries)

    actual_clusters = min(num_clusters, len(queries))
    kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X)

    feature_names = vectorizer.get_feature_names_out()
    clusters_info = []

    from collections import Counter
    for i in range(actual_clusters):
        center = kmeans.cluster_centers_[i]
        top_indices = center.argsort()[-5:][::-1]
        top_keywords = [feature_names[idx] for idx in top_indices if center[idx] > 0]
        if not top_keywords:
            top_keywords = ["query", "operation"]

        cluster_size = int(np.sum(labels == i))
        c_name = "Information & Operations"
        if any(k in top_keywords for k in ["delete", "remove", "update", "purge", "suspend"]):
            c_name = "System Modification & Mutation"
        elif any(k in top_keywords for k in ["email", "send", "alert", "notify"]):
            c_name = "External Alerting & Operations"
        elif any(k in top_keywords for k in ["user", "read", "fetch", "details", "log"]):
            c_name = "Data Retrieval & Verification"

        cluster_query_indices = np.where(labels == i)[0]
        sample_q = queries[cluster_query_indices[0]] if len(cluster_query_indices) > 0 else "Unknown operation"

        tools_in_cluster = []
        for idx in cluster_query_indices:
            s = scenarios[idx]
            if isinstance(s, dict):
                if "expected_tools" in s:
                    tools_in_cluster.extend(s["expected_tools"])
                elif "tools" in s:
                    tools_in_cluster.extend(s["tools"])
        
        top_tools = [t[0] for t in Counter(tools_in_cluster).most_common(2)] if tools_in_cluster else top_keywords[:2]

        clusters_info.append({
            "cluster_id": i,
            "intent": c_name,
            "keywords": top_keywords,
            "scenario_count": cluster_size,
            "primary_tools": top_tools,
            "sample_query": sample_q
        })

    return {
        "vectorizer": vectorizer,
        "kmeans": kmeans,
        "labels": labels.tolist(),
        "clusters": clusters_info
    }

def save_clustering_models(agent_id: str, vectorizer: TfidfVectorizer, kmeans: KMeans):
    path = os.path.join(MODEL_DIR, f"{agent_id}_clustering.pkl")
    with open(path, "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "kmeans": kmeans}, f)

def load_clustering_models(agent_id: str):
    path = os.path.join(MODEL_DIR, f"{agent_id}_clustering.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None
