"""
Device Master Repository - loads device_master.csv for stateless analysis.
Used by the /api/analyze/* endpoints so the MongoDB webapp can get EPR
analysis without needing Supabase sync.
"""

import os
import pandas as pd
from difflib import SequenceMatcher
from app.config import settings


class DeviceMasterRepository:
    def __init__(self):
        csv_path = settings.DEVICE_MASTER_CSV_PATH
        if not os.path.isabs(csv_path):
            # Resolve relative to project root
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            csv_path = os.path.join(base_dir, csv_path)

        self.df = pd.read_csv(csv_path)
        # Ensure imei_prefix is string
        self.df['imei_prefix'] = self.df['imei_prefix'].astype(str)

    async def get_device_by_imei_prefix(self, prefix: str):
        """Lookup device by first 8 digits of IMEI"""
        match = self.df[self.df['imei_prefix'] == prefix]
        if not match.empty:
            return self._row_to_dict(match.iloc[0])
        return None

    async def get_device_by_model_fuzzy(self, model_input: str):
        """Fuzzy match model name against CSV data"""
        best_match = None
        best_score = 0

        for _, row in self.df.iterrows():
            device = self._row_to_dict(row)
            aliases = []
            raw_aliases = device.get('search_aliases', '')
            if isinstance(raw_aliases, str) and raw_aliases:
                aliases = [a.strip() for a in raw_aliases.split(',')]
            aliases.append(device['model_name'])

            for alias in aliases:
                score = self._similarity(model_input.lower(), alias.lower())
                if score > best_score and score > 60:
                    best_score = score
                    best_match = device

        return best_match

    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0-100)"""
        if s1 in s2 or s2 in s1:
            return 80.0
        return SequenceMatcher(None, s1, s2).ratio() * 100

    def _row_to_dict(self, row) -> dict:
        """Convert a DataFrame row to a dict matching Supabase schema"""
        return {
            'id': str(row.get('imei_prefix', '')),  # Use prefix as ID for CSV
            'imei_prefix': str(row['imei_prefix']),
            'model_name': row['model_name'],
            'brand': row['brand'],
            'category_code': row['category_code'],
            'total_weight_kg': float(row['total_weight_kg']),
            'gold_g_per_ton': float(row.get('gold_g_per_ton', 0)),
            'copper_kg_per_ton': float(row.get('copper_kg_per_ton', 0)),
            'search_aliases': row.get('search_aliases', ''),
        }


# Singleton instance
device_master_repo = DeviceMasterRepository()
