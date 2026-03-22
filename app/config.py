from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SUPABASE_URL: str = "https://bipqgdlipdgqilchznia.supabase.co"
    SUPABASE_KEY: str = "sb_publishable_u4ByUUAvuwQPEJACmxuIQg_YvDP_F3h"
    DEVICE_MASTER_CSV_PATH: str = "data/device_master.csv"
    
    class Config:
        env_file = ".env"

settings = Settings()