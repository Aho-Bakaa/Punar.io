from app.database.supabase_client import SupabaseRepository

class DeviceResolver:
    def __init__(self, repo: SupabaseRepository = None):
        self.repo = repo or SupabaseRepository()
    
    async def resolve_device(self, device_data: dict):
        """
        Resolve device from your existing table to CPCB master data
        device_data comes from your devices table
        """
        imei = device_data.get('imei')
        model = device_data.get('model')
        device_type = device_data.get('device_type')
        brand = device_data.get('brand')
        
        # Strategy 1: IMEI lookup (first 8 digits)
        if imei and len(imei) >= 8:
            tac = imei[:8]
            master = await self.repo.get_device_by_imei_prefix(tac)
            if master:
                return self._format_result(master, confidence=0.95)
        
        # Strategy 2: Fuzzy model match
        if model:
            search_term = f"{brand} {model}" if brand else model
            master = await self.repo.get_device_by_model_fuzzy(search_term)
            if master:
                return self._format_result(master, confidence=0.80)
        
        # Strategy 3: Infer from device_type
        category_map = {
            'Smartphone': ('CEEW6', 0.18),
            'Mobile Phone': ('CEEW6', 0.18),
            'Laptop': ('ITEW4', 1.5),
            'Notebook': ('ITEW4', 1.5),
            'Desktop': ('ITEW3', 8.0),
            'Television': ('CEEW1', 12.0),
            'Refrigerator': ('CEEW2', 35.0)
        }
        
        cat_info = category_map.get(device_type, ('ITEW3', 1.0))
        
        return {
            'resolved': False,
            'device_master_id': None,
            'category_code': cat_info[0],
            'model': model or 'Unknown',
            'brand': brand or 'Generic',
            'total_weight_kg': cat_info[1],
            'components': None,
            'confidence': 0.50
        }
    
    def _format_result(self, master: dict, confidence: float):
        return {
            'resolved': True,
            'device_master_id': master['id'],
            'category_code': master['category_code'],
            'model': master['model_name'],
            'brand': master['brand'],
            'total_weight_kg': master['total_weight_kg'],
            'components': master.get('components'),
            'gold_g_per_ton': master.get('gold_g_per_ton', 0),
            'copper_kg_per_ton': master.get('copper_kg_per_ton', 0),
            'confidence': confidence
        }