import socket
import uvicorn
import logging
import os
import app.database as database

def find_available_port(start_port=8000, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return port
            except OSError:
                continue
    return start_port

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("startup")
    
    logger.info("Initializing baseline database schemas...")
    database.init_db()
    
    env_port = int(os.getenv("PORT", 7860))
    port = find_available_port(env_port)
    
    logger.info("==================================================")
    logger.info(f"✔ Server Online! Access UI at: http://localhost:{port}")
    logger.info("==================================================")
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
