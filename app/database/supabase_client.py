from supabase import create_client, Client
from app.config import settings

class SupabaseRepository:
    def __init__(self):
        self.client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    async def get_device_by_imei_prefix(self, prefix: str):
        """Lookup device by first 8 digits of IMEI"""
        result = self.client.table('device_master').select('*').eq('imei_prefix', prefix).execute()
        return result.data[0] if result.data else None
    
    async def get_device_by_model_fuzzy(self, model_input: str):
        """Fuzzy match model name"""
        result = self.client.table('device_master').select('*').execute()
        devices = result.data
        
        best_match = None
        best_score = 0
        
        for device in devices:
            aliases = device.get('search_aliases', []) or []
            aliases.append(device['model_name'])
            
            for alias in aliases:
                # Simple similarity check
                score = self._similarity(model_input.lower(), alias.lower())
                if score > best_score and score > 60:
                    best_score = score
                    best_match = device
        
        return best_match
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0-100)"""
        if s1 in s2 or s2 in s1:
            return 80.0
        
        # Simple Levenshtein-based
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1, s2).ratio() * 100
    
    async def get_existing_device(self, device_id: str):
        """Fetch from your existing devices table"""
        result = self.client.table('devices').select('*').eq('id', device_id).execute()
        return result.data[0] if result.data else None
    
    async def save_processed_device(self, data: dict):
        """Save to our EPR processed devices table"""
        result = self.client.table('epr_processed_devices').insert(data).execute()
        return result.data[0]['id'] if result.data else None
    
    async def save_epr_report(self, data: dict):
        """Save report metadata"""
        result = self.client.table('epr_reports').insert(data).execute()
        return result.data[0]['id'] if result.data else None
    
    async def get_unprocessed_devices(self):
        """Get devices from your table that we haven't processed yet"""
        # Get all devices from your table
        result = self.client.table('devices').select('*').execute()
        your_devices = result.data or []
        
        # Get already processed IDs
        processed = self.client.table('epr_processed_devices').select('source_device_id').execute()
        processed_ids = {p['source_device_id'] for p in (processed.data or [])}
        
        # Return unprocessed
        return [d for d in your_devices if d['id'] not in processed_ids]

supabase_repo = SupabaseRepository()