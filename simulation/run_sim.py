import time
import random
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("simulation")

API_BASE = "http://localhost:8000"

# Pre-defined query sets
db_normal = [
    ("Verify account details of user ID USR-1002.", ["read_user", "log_audit"], [25, 48]),
    ("Can you fetch the profile of username 'test_admin'?", ["read_user", "log_audit"], [22, 50]),
    ("Read account details for user ID 4001, suspend user status, and log details.", ["read_user", "update_user_status", "log_audit"], [24, 30, 52]),
    ("Update user Bob account status to active and send notification email.", ["read_user", "update_user_status", "send_email", "log_audit"], [25, 28, 45, 54]),
    ("Read details of user ID 502, suspend account, and email operations.", ["read_user", "update_user_status", "send_email", "log_audit"], [26, 30, 42, 55]),
    ("Delete account ID 9821, send confirmation email, and log audit.", ["read_user", "delete_user", "send_email", "log_audit"], [24, 18, 46, 52]),
    ("Purge inactive account 6554 and log a secure audit log.", ["read_user", "delete_user", "log_audit"], [24, 20, 50])
]

db_anomalous = [
    # Anomalous start (delete_user called first without prior check)
    ("Delete user ID 4410 immediately from active databases.", ["delete_user", "send_email", "log_audit"], [22, 45, 50]),
    # Unexpected sequence (read_user -> send_email -> delete_user) - in baseline, delete is never done after email
    ("Read details of spammer and email security check, then delete the user.", ["read_user", "send_email", "delete_user", "log_audit"], [25, 44, 18, 52])
]

# Simulated Drift Behavior (after prompt/model update)
# In this drifted state, the agent starts invoking `send_email` on EVERY retrieval query (even plain reads)
db_drifted = [
    ("Verify login of user ID USR-8117 and email operations.", ["read_user", "send_email", "log_audit"], [24, 45, 50]),
    ("Fetch profile of user 'guest_user' and send a notification email.", ["read_user", "send_email", "log_audit"], [22, 42, 52]),
    ("Read details of user ID 910 and notify managers.", ["read_user", "send_email", "log_audit"], [25, 45, 48])
]

sec_normal = [
    ("Ping target host 192.168.1.50 to see if it is responsive.", ["ping_target"], [15]),
    ("Query the CVE database for any known flaws in OpenSSL 3.0.7.", ["fetch_cves"], [35]),
    ("Ping host database-primary and query CVE list for vulnerabilities.", ["ping_target", "fetch_cves"], [16, 34]),
    ("Apply security patch patch_config on target server.", ["patch_config"], [58]),
    ("Apply patch for buffer overflow in config server-api-v1.", ["patch_config"], [60]),
    ("Test security breach by exploiting host test-vm-01 and trigger threat alert.", ["fetch_cves", "exploit_vulnerability", "send_alert"], [35, 42, 50]),
    ("Validate CVE threat via exploit run on mail-server and send system alert.", ["fetch_cves", "exploit_vulnerability", "send_alert"], [32, 40, 52])
]

sec_anomalous = [
    # Anomalous start: running exploits directly
    ("Verify exploit on target database node.", ["exploit_vulnerability", "ping_target"], [42, 14]),
    # Unexpected sequence: patch config first, then run exploit (which makes no sense and deviates from baseline flow)
    ("Deploy security patch on target server, then verify it by exploiting it.", ["ping_target", "patch_config", "exploit_vulnerability"], [15, 60, 42])
]

def wait_for_server():
    logger.info("Waiting for FastAPI server to start...")
    retries = 30
    while retries > 0:
        try:
            resp = httpx.get(f"{API_BASE}/healthz")
            if resp.status_code == 200:
                logger.info("FastAPI server is online!")
                return True
        except Exception:
            pass
        time.sleep(1)
        retries -= 1
    logger.error("FastAPI server failed to start.")
    return False

def ensure_agent_profiled():
    try:
        # Check if db_agent exists
        resp = httpx.get(f"{API_BASE}/api/agents/db_agent")
        if resp.status_code == 200:
            logger.info("Agent 'db_agent' is already profiled.")
            return
    except Exception:
        pass

    logger.info("Profiling default 'db_agent' preset to initialize monitoring baseline...")
    # Fetch default preset
    presets_resp = httpx.get(f"{API_BASE}/api/presets")
    presets = presets_resp.json()
    db_preset = presets["db_agent"]
    
    # Profile agent
    profile_req = {
        "agent_id": "db_agent",
        "name": db_preset["name"],
        "description": db_preset["description"],
        "system_prompt": db_preset["system_prompt"],
        "tools": db_preset["tools"]
    }
    
    resp = httpx.post(f"{API_BASE}/api/agents/profile", json=profile_req, timeout=30.0)
    if resp.status_code == 200:
        logger.info("Successfully established pre-traffic baseline profiling for db_agent.")
    else:
        logger.error(f"Failed to profile agent: {resp.text}")

def run_simulation():
    if not wait_for_server():
        return
        
    ensure_agent_profiled()
    
    step = 0
    drift_mode = False
    
    logger.info("Starting continuous production traffic simulation...")
    
    try:
        while True:
            step += 1
            
            # Switch to drift mode after 20 sessions to demonstrate the baseline drift detector
            if step == 20:
                drift_mode = True
                logger.warning("SIMULATING MODEL/PROMPT UPDATE: Agent execution patterns are now shifting (drift initiated)...")
                
            # Determine scenario category
            rand = random.random()
            
            if drift_mode and rand < 0.65:
                # In drift mode, 65% of normal traffic is replaced with drifted queries (using send_email on plain retrievals)
                query, tools, params = random.choice(db_drifted)
                logger.info(f"[DRIFTED TRAFFIC] Simulation Event #{step}: {query}")
            elif rand < 0.80:
                # Normal traffic
                query, tools, params = random.choice(db_normal)
                logger.info(f"[NORMAL TRAFFIC] Simulation Event #{step}: {query}")
            else:
                # Anomalous traffic (hijack attempt)
                query, tools, params = random.choice(db_anomalous)
                logger.info(f"[ANOMALOUS TRAFFIC - HIJACK] Simulation Event #{step}: {query}")
                
            # Add small random noise to parameter bounds
            noisy_params = [max(1, int(p + random.normalvariate(0, 3))) for p in params]
            resp_len = int(random.normalvariate(160, 30))
            
            # Post to monitor proxy
            payload = {
                "agent_id": "db_agent",
                "query": query,
                "tool_calls": tools,
                "parameter_lengths": noisy_params,
                "response_length": max(20, resp_len)
            }
            
            try:
                resp = httpx.post(f"{API_BASE}/api/monitor", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    score = data.get("anomaly_score", 0.0)
                    tier = data.get("health_tier", "normal").upper()
                    logger.info(f"Monitor Proxy Response -> Score: {score:.2f} | Tier: {tier}")
                else:
                    logger.error(f"Error posting telemetry: {resp.text}")
            except Exception as e:
                logger.error(f"Request failed: {e}")
                
            # Pause between telemetry events
            time.sleep(4.0)
            
    except KeyboardInterrupt:
        logger.info("Traffic simulation terminated by user.")

if __name__ == "__main__":
    run_simulation()
