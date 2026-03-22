from datetime import datetime
from typing import List, Dict
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

class ReportGenerator:
    def __init__(self, repo):
        self.repo = repo
    
    async def generate_dashboard_data(
        self, 
        producer_name: str, 
        producer_reg: str, 
        period: str
    ) -> Dict:
        """
        Generate JSON data for dashboards (no PDF)
        """
        # Get unprocessed devices from source table
        devices = await self.repo.get_unprocessed_devices()
        
        if not devices:
            return {
                "summary": None,
                "devices": [],
                "message": "No unprocessed devices found"
            }
        
        # Process all devices
        processed = []
        state_totals = {}
        category_totals = {}
        
        total_refurb = 0
        total_recycle = 0
        total_carbon = 0
        total_gold = 0
        total_copper = 0
        total_lithium = 0
        
        from app.services.device_resolver import DeviceResolver
        from app.services.weight_calculator import WeightCalculator
        
        resolver = DeviceResolver(self.repo)
        calculator = WeightCalculator()
        
        for device in devices:
            # Resolve device
            resolved = await resolver.resolve_device(device)
            
            # Determine channelization
            channelization = calculator.determine_channelization(
                device.get('condition', 'Working'),
                device.get('recycler_name')
            )
            
            # Calculate weight
            weight_calc = calculator.calculate_accountable_weight(
                resolved['total_weight_kg'],
                device.get('condition', 'Working'),
                channelization
            )
            
            # Calculate materials
            materials = calculator.calculate_materials(
                weight_calc['accountable_weight_kg'],
                resolved.get('gold_g_per_ton', 0),
                resolved.get('copper_kg_per_ton', 0),
                resolved.get('lithium_kg_per_ton', 0)
            )
            
            # Calculate carbon (based on weight × carbon factor)
            carbon_factor = resolved.get('carbon_saved_per_kg', 300)  # kg CO2 per kg device
            carbon_saved = weight_calc['accountable_weight_kg'] * carbon_factor
            
            # Save to processed table
            record = {
                'source_device_id': device['id'],
                'device_master_id': resolved.get('device_master_id'),
                'collection_state': device.get('collection_state', 'Unknown'),
                'resolved_category': resolved['category_code'],
                'condition_assessment': device.get('condition', 'Working'),
                'channelization_type': channelization,
                'standard_weight_kg': weight_calc['standard_weight_kg'],
                'condition_factor': weight_calc['condition_factor'],
                'accountable_weight_kg': weight_calc['accountable_weight_kg'],
                'estimated_gold_g': materials['gold_g'],
                'estimated_copper_kg': materials['copper_kg'],
                'estimated_lithium_kg': materials.get('lithium_kg', 0),
                'carbon_avoided_kg': carbon_saved
            }
            
            processed_id = await self.repo.save_processed_device(record)
            
            # Aggregate totals
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
            
            # Add to processed list for response
            processed.append({
                "id": processed_id,
                "source_device_id": device['id'],
                "model": resolved['model'],
                "brand": resolved['brand'],
                "category_code": resolved['category_code'],
                "condition": device.get('condition', 'Working'),
                "channelization_type": channelization,
                "accountable_weight_kg": weight_calc['accountable_weight_kg'],
                "collection_state": state,
                "estimated_gold_g": materials['gold_g'],
                "estimated_copper_kg": materials['copper_kg'],
                "processed_at": datetime.now().isoformat()
            })
        
        # Calculate compliance metrics
        total_weight = total_refurb + total_recycle
        target_required = total_weight * 0.7  # 70% target as per CPCB
        compliance_pct = (total_weight / target_required * 100) if target_required > 0 else 0
        
        # Build summary
        summary = {
            "producer_name": producer_name,
            "reporting_period": period,
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
        
        # Save report metadata
        report_data = {
            "producer_name": producer_name,
            "producer_cpcb_reg": producer_reg,
            "reporting_period": period,
            "total_devices": summary["total_devices"],
            "total_weight_kg": summary["total_weight_kg"],
            "refurbishment_weight_kg": summary["refurbishment_weight_kg"],
            "recycling_weight_kg": summary["recycling_weight_kg"],
            "target_required_kg": summary["target_required_kg"],
            "compliance_percentage": summary["compliance_percentage"],
            "carbon_avoided_kg": summary["carbon_avoided_kg"],
            "total_gold_g": summary["total_gold_g"],
            "total_copper_kg": summary["total_copper_kg"],
            "total_lithium_kg": summary["total_lithium_kg"],
            "state_breakdown": state_totals,
            "category_breakdown": category_totals
        }
        
        report_id = await self.repo.save_epr_report(report_data)
        
        return {
            "report_id": report_id,
            "summary": summary,
            "devices": processed,
            "state_breakdown": state_totals,
            "category_breakdown": category_totals
        }
    
    async def generate_pdf_report(self, report_id: str, data: Dict) -> str:
        """
        Optional: Generate PDF if needed for CPCB upload
        """
        summary = data["summary"]
        filename = f"reports/EPR_Report_{report_id}.pdf"
        
        doc = SimpleDocTemplate(filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Title
        story.append(Paragraph(f"<b>EPR Compliance Report - {summary['producer_name']}</b>", styles['Title']))
        story.append(Paragraph(f"Period: {summary['reporting_period']}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Summary Table (CPCB Format)
        table_data = [
            ['Metric', 'Value'],
            ['Total Devices Processed', str(summary['total_devices'])],
            ['Total E-Waste (kg)', f"{summary['total_weight_kg']:.2f}"],
            ['Target Required (kg)', f"{summary['target_required_kg']:.2f}"],
            ['Compliance Percentage', f"{summary['compliance_percentage']:.2f}%"],
            ['Carbon Avoided (kg)', f"{summary['carbon_avoided_kg']:.2f}"],
            ['Gold Recovered (g)', f"{summary['total_gold_g']:.2f}"],
            ['Copper Recovered (kg)', f"{summary['total_copper_kg']:.2f}"],
            ['Lithium Recovered (kg)', f"{summary['total_lithium_kg']:.2f}"]
        ]
        
        table = Table(table_data, colWidths=[250, 150])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        story.append(table)
        
        doc.build(story)
        return filename