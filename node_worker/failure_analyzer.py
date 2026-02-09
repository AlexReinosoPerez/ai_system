"""
Failure Analyzer - Detects failed executions from reports.json

Responsibility: Read reports.json and identify failed DDS executions.
NO execution, NO decision making, NO side effects.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Set
from datetime import datetime


class FailureAnalyzer:
    """
    Analyzes execution reports to detect failures.
    
    Pure detection logic - no side effects.
    Keeps a set of already-processed DDS IDs to avoid re-proposing
    fixes for failures that have already been handled.
    """
    
    REPORTS_FILE = Path("node_programmer/reports.json")
    
    def __init__(self):
        self._processed_dds_ids: Set[str] = set()
    
    def mark_processed(self, dds_id: str) -> None:
        """Mark a DDS ID as already processed (fix proposed or skipped)."""
        self._processed_dds_ids.add(dds_id)
    
    # Error patterns that indicate env/infra issues — NOT fixable by code_fix
    _UNFIXABLE_PATTERNS = [
        "timeout",          # Execution timeout — no diagnostic info
        "timed out",        # Variant
        "rate limit",       # API rate limiting — transient
        "connection refused",  # Network — transient
        "503",              # Service unavailable — transient
        "command not found",   # Tool not installed — infra
        "aider: not found",    # Aider missing — infra
    ]

    def _is_unfixable_error(self, error_message: str) -> bool:
        """Check if error is env/infra related and should NOT generate a fix."""
        msg_lower = error_message.lower()
        return any(pattern in msg_lower for pattern in self._UNFIXABLE_PATTERNS)
    
    def get_latest_failure(self) -> Optional[Dict]:
        """
        Get the most recent unprocessed failed execution from reports.json.
        
        Scans backwards through executions to find the latest failure
        that has not already been processed (i.e., a fix hasn't been
        proposed or explicitly skipped for it).
        
        Returns:
            Dict with failure info or None if no unprocessed failures
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
            
            # Scan backwards to find latest unprocessed failure
            for entry in reversed(executions):
                if entry.get('status') != 'failed':
                    continue
                
                # Only process code_change or code_fix types
                action_type = entry.get('action_type', '')
                if action_type not in ['code_change', 'code_fix']:
                    continue
                
                dds_id = entry.get('dds_id', '')
                
                # Skip already-processed failures
                if dds_id in self._processed_dds_ids:
                    continue
                
                # Skip unfixable errors (timeout, infra, transient)
                error_msg = entry.get('notes', '')
                if self._is_unfixable_error(error_msg):
                    continue
                
                return {
                    'dds_id': dds_id,
                    'error_message': error_msg,
                    'failed_at': entry.get('executed_at', datetime.now().isoformat()),
                    'action_type': action_type
                }
            
            return None
            
        except (json.JSONDecodeError, IOError) as e:
            raise RuntimeError(f"Error reading reports.json: {e}")
