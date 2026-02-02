"""
Programmer - DDS execution engine with noop actions
"""

import json
import os
from datetime import datetime
from typing import List, Optional
from node_programmer.execution_report import ExecutionReport
from shared.logger import setup_logger

logger = setup_logger(__name__)


class ProgrammerError(Exception):
    """Raised when programmer operations fail"""
    pass


class Programmer:
    """Executes approved DDS proposals with controlled actions"""
    
    REPORTS_FILE = "node_programmer/reports.json"
    SANDBOX_DIR = "node_programmer/sandbox"
    DDS_FILE = "node_dds/dds.json"
    
    def __init__(self):
        """Initialize programmer"""
        logger.info("Programmer initialized")
        os.makedirs(self.SANDBOX_DIR, exist_ok=True)
    
    def _load_reports(self) -> List[ExecutionReport]:
        """Load execution reports from JSON"""
        if not os.path.exists(self.REPORTS_FILE):
            logger.warning(f"Reports file not found: {self.REPORTS_FILE}")
            return []
        
        try:
            with open(self.REPORTS_FILE, 'r') as f:
                data = json.load(f)
            
            executions_data = data.get('executions', [])
            reports = [ExecutionReport.from_dict(e) for e in executions_data]
            logger.info(f"Loaded {len(reports)} execution reports")
            return reports
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reports.json: {e}")
            raise ProgrammerError(f"Invalid JSON format: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to load reports: {e}")
            raise ProgrammerError(f"Error loading reports: {str(e)}") from e
    
    def _save_report(self, report: ExecutionReport):
        """Save execution report to JSON"""
        try:
            reports = self._load_reports()
            reports.append(report)
            
            data = {
                'executions': [r.to_dict() for r in reports]
            }
            
            with open(self.REPORTS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved execution report for {report.dds_id}")
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            raise ProgrammerError(f"Error saving report: {str(e)}") from e
    
    def _get_approved_dds(self) -> list:
        """Get approved DDS proposals"""
        if not os.path.exists(self.DDS_FILE):
            logger.warning(f"DDS file not found: {self.DDS_FILE}")
            return []
        
        try:
            with open(self.DDS_FILE, 'r') as f:
                data = json.load(f)
            
            proposals = data.get('proposals', [])
            approved = [p for p in proposals if p.get('status') == 'approved']
            logger.info(f"Found {len(approved)} approved DDS proposals")
            return approved
            
        except Exception as e:
            logger.error(f"Failed to load DDS proposals: {e}")
            raise ProgrammerError(f"Error loading DDS: {str(e)}") from e
    
    def _is_already_executed(self, dds_id: str) -> bool:
        """Check if DDS has already been executed"""
        reports = self._load_reports()
        
        for report in reports:
            if report.dds_id == dds_id:
                logger.info(f"DDS {dds_id} already executed")
                return True
        
        return False
    
    def execute_noop(self, dds_id: str) -> ExecutionReport:
        """
        Execute noop action for DDS proposal
        
        Args:
            dds_id: DDS proposal ID to execute
            
        Returns:
            ExecutionReport with execution details
            
        Raises:
            ProgrammerError: If execution fails
        """
        logger.info(f"Executing noop for DDS: {dds_id}")
        
        # Check if already executed
        if self._is_already_executed(dds_id):
            raise ProgrammerError(f"DDS {dds_id} has already been executed")
        
        # Verify DDS is approved
        approved_dds = self._get_approved_dds()
        dds_found = None
        for dds in approved_dds:
            if dds.get('id') == dds_id:
                dds_found = dds
                break
        
        if not dds_found:
            raise ProgrammerError(f"DDS {dds_id} not found or not approved")
        
        # Execute noop action
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"noop_{dds_id}_{timestamp}.txt"
            filepath = os.path.join(self.SANDBOX_DIR, filename)
            
            executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            content = f"DDS {dds_id} executed at {executed_at}"
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            logger.info(f"Created sandbox file: {filename}")
            
            # Create execution report
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='noop',
                status='success',
                executed_at=executed_at,
                notes=f"Noop action completed. File: {filename}"
            )
            
            # Save report
            self._save_report(report)
            
            logger.info(f"Successfully executed DDS {dds_id}")
            return report
            
        except Exception as e:
            logger.error(f"Execution failed for DDS {dds_id}: {e}")
            
            # Create failure report
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='noop',
                status='failed',
                executed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                notes=f"Execution failed: {str(e)}"
            )
            
            self._save_report(report)
            raise ProgrammerError(f"Execution failed: {str(e)}") from e
    
    def get_last_report(self) -> Optional[ExecutionReport]:
        """
        Get most recent execution report
        
        Returns:
            Last ExecutionReport or None if no executions
        """
        reports = self._load_reports()
        
        if not reports:
            logger.info("No execution reports found")
            return None
        
        return reports[-1]
