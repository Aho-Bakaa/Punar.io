class WeightCalculator:
    def __init__(self):
        # Condition factors
        self.condition_map = {
            'Mint': 1.0,
            'Excellent': 1.0,
            'Good': 0.95,
            'Working': 0.90,
            'Fair': 0.75,
            'Damaged': 0.60,
            'Broken': 0.40,
            'Non-working': 0.35,
            'Crushed': 0.25,
            'pristine': 1.0,
            'screen_damage': 0.85,
            'battery_missing': 0.75,
            'non_working': 0.60
        }
    
    def calculate_accountable_weight(
        self, 
        standard_weight: float, 
        condition: str,
        channelization: str,
        components: dict = None
    ):
        """
        Calculate weight for EPR report
        """
        # Get condition factor
        factor = self.condition_map.get(condition, 0.80)
        
        if channelization == 'refurbishment':
            # For refurbishment, use full weight (device preserved)
            accountable = standard_weight
        else:
            # For recycling, apply condition factor
            accountable = standard_weight * factor
        
        return {
            'standard_weight_kg': round(standard_weight, 3),
            'condition_factor': factor,
            'accountable_weight_kg': round(accountable, 3),
            'channelization_type': channelization
        }
    
    def determine_channelization(self, condition: str, recycler_name: str = None):
        """
        INFER channelization from existing data (no new column needed)
        Logic: 
        - Good condition + no recycler = Refurbishment
        - Bad condition or recycler present = Recycling
        """
        good_conditions = ['Mint', 'Excellent', 'Good', 'Working', 'pristine']
        
        if condition in good_conditions and not recycler_name:
            return 'refurbishment'
        
        return 'recycling'
    
    def calculate_materials(self, weight_kg: float, gold_rate: float, copper_rate: float):
        """Calculate material recovery estimates"""
        tons = weight_kg / 1000
        return {
            'gold_g': round(gold_rate * tons, 2),
            'copper_kg': round(copper_rate * tons, 2)
        }