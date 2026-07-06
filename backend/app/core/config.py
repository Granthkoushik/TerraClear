from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "TerraClear LISS-IV Cloud Removal & Surface Reconstruction"
    API_V1_STR: str = "/api"
    
    # Base paths
    BASE_DIR: Path = Path("c:/TerraClear")
    DATA_DIR: Path = Path("c:/TerraClear/data")
    UPLOAD_DIR: Path = Path("c:/TerraClear/data/uploads")
    PROCESSED_DIR: Path = Path("c:/TerraClear/data/processed")
    
    # Models configuration
    WEIGHTS_DIR: Path = Path("c:/TerraClear/backend/weights")
    CLOUD_DETECTION_MODEL_PATH: Path = Path("c:/TerraClear/backend/weights/cloud_detector.pth")
    RECONSTRUCTION_MODEL_PATH: Path = Path("c:/TerraClear/backend/weights/reconstruction_net.pth")
    
    # Mode configurations
    ALLOW_CLASSICAL_FALLBACK: bool = True
    DEFAULT_DETECTION_THRESHOLD: float = 0.5
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
