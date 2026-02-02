"""
Failure Analyzer - Detects failed executions from reports.json

Responsibility: Read reports.json and identify failed DDS executions.
NO execution, NO decision making, NO side effects.
"""

import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime


class FailureAnalyzer:
    """
    Analyzes execution reports to detect failures.
    
    Pure detection logic - no side effects.
    """
    
    REPORTS_FILE = Path("node_programmer/reports.json")
    
    def get_latest_failure(self) -> Optional[Dict]:
        """
        Get the most recent failed execution from reports.json
        
        Returns:
            Dict with failure info or None if no failures
            {
                "dds_id": str,
                "error_message": str,
                "failed_at": str,
                "action_type": str
            }
        """
        if not self.REPORTS_FILE.exists():
            return None
        
        try:
            with open(self.REPORTS_FILE, 'r') as f:
                data = json.load(f)
            
            executions = data.get('executions', [])
            
            if not executions:
                return None
            
            # Get most recent execution
            latest = executions[-1]
            
            # Check if it's a failure
            if latest.get('status') != 'failure':
                return None
            
            # Only process code_change or code_fix types
            action_type = latest.get('action_type', '')
            if action_type not in ['code_change', 'code_fix']:
                return None
            
            return {
                'dds_id': latest.get('dds_id', ''),
                'error_message': latest.get('notes', ''),
                'failed_at': latest.get('executed_at', datetime.now().isoformat()),
                'action_type': action_type
            }
            
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"Error reading reports.json: {e}")
