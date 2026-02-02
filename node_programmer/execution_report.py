"""
Execution Report - Data structure for DDS execution reports
"""

from dataclasses import dataclass


@dataclass
class ExecutionReport:
    """Represents a DDS execution report"""
    
    dds_id: str
    action_type: str
    status: str
    executed_at: str
    notes: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'dds_id': self.dds_id,
            'action_type': self.action_type,
            'status': self.status,
            'executed_at': self.executed_at,
            'notes': self.notes
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ExecutionReport':
        """Create report from dictionary"""
        return ExecutionReport(
            dds_id=data['dds_id'],
            action_type=data['action_type'],
            status=data['status'],
            executed_at=data['executed_at'],
            notes=data['notes']
        )
