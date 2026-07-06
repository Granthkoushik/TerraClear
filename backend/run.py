import uvicorn
import sys
from pathlib import Path

# Append the absolute path of the backend directory and backend/app directory
backend_dir = Path(__file__).parent.resolve()
sys.path.append(str(backend_dir))
sys.path.append(str(backend_dir / "app"))

if __name__ == "__main__":
    logger_msg = "Starting TerraClear FastAPI Server on http://localhost:8000"
    print(logger_msg)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
