"""
DDS Proposal - Data structure for decision proposals
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class DDSProposal:
    """Represents a DDS proposal.
    
    Core fields (always present):
        id, project, title, description, created_at, status
    
    Extended fields (present on code_fix proposals):
        dds_type, source_dds, error_context, constraints, allowed_paths
    """
    
    id: str
    project: str
    title: str
    description: str
    created_at: str
    status: str
    # Execution fields — needed by Programmer to execute the DDS
    version: Optional[int] = None
    goal: Optional[str] = None
    instructions: Optional[List[str]] = field(default=None, repr=False)
    tool: Optional[str] = None
    # Extended fields — populated by FixDDSGenerator, absent on simple proposals
    dds_type: Optional[str] = None
    source_dds: Optional[str] = None
    error_context: Optional[Dict] = field(default=None, repr=False)
    constraints: Optional[Dict] = field(default=None, repr=False)
    allowed_paths: Optional[List[str]] = field(default=None, repr=False)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization.
        Extended fields are only included when they have a value."""
        d = {
            'id': self.id,
            'project': self.project,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at,
            'status': self.status
        }
        # Execution fields — only persist when set
        if self.version is not None:
            d['version'] = self.version
        if self.goal is not None:
            d['goal'] = self.goal
        if self.instructions is not None:
            d['instructions'] = self.instructions
        if self.tool is not None:
            d['tool'] = self.tool
        # Extended fields — only persist when set
        if self.dds_type is not None:
            d['type'] = self.dds_type
        if self.source_dds is not None:
            d['source_dds'] = self.source_dds
        if self.error_context is not None:
            d['error_context'] = self.error_context
        if self.constraints is not None:
            d['constraints'] = self.constraints
        if self.allowed_paths is not None:
            d['allowed_paths'] = self.allowed_paths
        return d
    
    @staticmethod
    def from_dict(data: dict) -> 'DDSProposal':
        """Create proposal from dictionary"""
        return DDSProposal(
            id=data['id'],
            project=data.get('project', 'unknown'),
            title=data.get('title', data.get('type', 'untitled')),
            description=data.get('description', ''),
            created_at=data.get('created_at', ''),
            status=data.get('status', 'unknown'),
            version=data.get('version'),
            goal=data.get('goal'),
            instructions=data.get('instructions'),
            tool=data.get('tool'),
            dds_type=data.get('type'),
            source_dds=data.get('source_dds'),
            error_context=data.get('error_context'),
            constraints=data.get('constraints'),
            allowed_paths=data.get('allowed_paths'),
        )
