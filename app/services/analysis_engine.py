"""
Stateless Analysis Engine — processes device data directly (no Supabase reads/writes).
The MongoDB webapp sends device data via the API, this engine runs EPR analysis
and returns results. The webapp persists results in its own MongoDB.
"""

from datetime import datetime
from typing import List, Dict
from app.services.device_resolver import DeviceResolver
from app.services.weight_calculator import WeightCalculator
from app.database.device_master_repo import device_master_repo


class AnalysisEngine:
    def __init__(self):
        self.resolver = DeviceResolver(device_master_repo)
        self.calculator = WeightCalculator()

    async def analyze_single_device(
        self,
        device_data: dict,
        override_channelization: str = None
    ) -> dict:
        """
        Analyze a single device — used by POST /api/analyze/device.
        Takes raw device data from MongoDB, returns EPR analysis.
        """
        resolved = await self.resolver.resolve_device(device_data)

        channelization = override_channelization or self.calculator.determine_channelization(
            device_data.get('condition', 'Working'),
            device_data.get('recycler_name')
        )

        weight_calc = self.calculator.calculate_accountable_weight(
            resolved['total_weight_kg'],
            device_data.get('condition', 'Working'),
            channelization
        )

        materials = self.calculator.calculate_materials(
            weight_calc['accountable_weight_kg'],
            resolved.get('gold_g_per_ton', 0),
            resolved.get('copper_kg_per_ton', 0)
        )

        carbon_factor = resolved.get('carbon_saved_per_kg', 300)
        carbon_saved = weight_calc['accountable_weight_kg'] * carbon_factor

        return {
            "device": {
                "device_id": device_data.get('device_id') or device_data.get('id', 'unknown'),
                "model": resolved['model'],
                "brand": resolved['brand'],
                "category": resolved['category_code'],
                "resolved": resolved.get('resolved', False),
                "confidence": resolved.get('confidence', 0)
            },
            "weight_data": {
                "standard_kg": weight_calc['standard_weight_kg'],
                "accountable_kg": weight_calc['accountable_weight_kg'],
                "condition_factor": weight_calc['condition_factor'],
                "channelization": channelization
            },
            "environmental_impact": {
                "carbon_avoided_kg": round(carbon_saved, 2),
                "gold_g": materials['gold_g'],
                "copper_kg": materials['copper_kg'],
                "lithium_kg": materials.get('lithium_kg', 0)
            },
            "analyzed_at": datetime.now().isoformat()
        }

    async def analyze_batch(
        self,
        devices: List[dict],
        producer_name: str,
        producer_cpcb_reg: str,
        reporting_period: str
    ) -> Dict:
        """
        Analyze multiple devices — used by POST /api/analyze/batch.
        Returns full dashboard data: summary + per-device + breakdowns.
        """
        if not devices:
            return {
                "summary": None,
                "devices": [],
                "state_breakdown": {},
                "category_breakdown": {},
                "message": "No devices provided"
            }

        processed = []
        state_totals = {}
        category_totals = {}

        total_refurb = 0
        total_recycle = 0
        total_carbon = 0
        total_gold = 0
        total_copper = 0
        total_lithium = 0

        for device in devices:
            resolved = await self.resolver.resolve_device(device)

            channelization = self.calculator.determine_channelization(
                device.get('condition', 'Working'),
                device.get('recycler_name')
            )

            weight_calc = self.calculator.calculate_accountable_weight(
                resolved['total_weight_kg'],
                device.get('condition', 'Working'),
                channelization
            )

            materials = self.calculator.calculate_materials(
                weight_calc['accountable_weight_kg'],
                resolved.get('gold_g_per_ton', 0),
                resolved.get('copper_kg_per_ton', 0)
            )

            carbon_factor = resolved.get('carbon_saved_per_kg', 300)
            carbon_saved = weight_calc['accountable_weight_kg'] * carbon_factor

            # Aggregations
            if channelization == 'refurbishment':
                total_refurb += weight_calc['accountable_weight_kg']
            else:
                total_recycle += weight_calc['accountable_weight_kg']

            total_carbon += carbon_saved
            total_gold += materials['gold_g']
            total_copper += materials['copper_kg']
            total_lithium += materials.get('lithium_kg', 0)

            # State breakdown
            state = device.get('collection_state', 'Unknown')
            if state not in state_totals:
                state_totals[state] = {"count": 0, "weight": 0, "recycling": 0, "refurbishment": 0}
            state_totals[state]["count"] += 1
            state_totals[state]["weight"] += weight_calc['accountable_weight_kg']
            if channelization == 'recycling':
                state_totals[state]["recycling"] += weight_calc['accountable_weight_kg']
            else:
                state_totals[state]["refurbishment"] += weight_calc['accountable_weight_kg']

            # Category breakdown
            cat = resolved['category_code']
            if cat not in category_totals:
                category_totals[cat] = {"count": 0, "weight": 0}
            category_totals[cat]["count"] += 1
            category_totals[cat]["weight"] += weight_calc['accountable_weight_kg']

            device_id = device.get('device_id') or device.get('id', f'device-{len(processed)}')
            processed.append({
                "device_id": device_id,
                "model": resolved['model'],
                "brand": resolved['brand'],
                "category_code": resolved['category_code'],
                "condition": device.get('condition', 'Working'),
                "channelization_type": channelization,
                "standard_weight_kg": weight_calc['standard_weight_kg'],
                "accountable_weight_kg": weight_calc['accountable_weight_kg'],
                "condition_factor": weight_calc['condition_factor'],
                "collection_state": state,
                "estimated_gold_g": materials['gold_g'],
                "estimated_copper_kg": materials['copper_kg'],
                "estimated_lithium_kg": materials.get('lithium_kg', 0),
                "carbon_avoided_kg": round(carbon_saved, 2),
                "resolved": resolved.get('resolved', False),
                "confidence": resolved.get('confidence', 0),
                "analyzed_at": datetime.now().isoformat()
            })

        # Compliance metrics
        total_weight = total_refurb + total_recycle
        target_required = total_weight * 0.7  # 70% target per CPCB
        compliance_pct = (total_weight / target_required * 100) if target_required > 0 else 0

        summary = {
            "producer_name": producer_name,
            "producer_cpcb_reg": producer_cpcb_reg,
            "reporting_period": reporting_period,
            "total_devices": len(processed),
            "total_weight_kg": round(total_weight, 2),
            "refurbishment_weight_kg": round(total_refurb, 2),
            "recycling_weight_kg": round(total_recycle, 2),
            "target_required_kg": round(target_required, 2),
            "compliance_percentage": round(compliance_pct, 2),
            "carbon_avoided_kg": round(total_carbon, 2),
            "total_gold_g": round(total_gold, 2),
            "total_copper_kg": round(total_copper, 2),
            "total_lithium_kg": round(total_lithium, 2),
            "generated_at": datetime.now().isoformat()
        }

        return {
            "summary": summary,
            "devices": processed,
            "state_breakdown": state_totals,
            "category_breakdown": category_totals
        }
