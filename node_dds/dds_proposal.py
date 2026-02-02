"""
DDS Proposal - Data structure for decision proposals
"""

from dataclasses import dataclass


@dataclass
class DDSProposal:
    """Represents a DDS proposal"""
    
    id: str
    project: str
    title: str
    description: str
    created_at: str
    status: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'project': self.project,
            'title': self.title,
            'description': self.description,
            'created_at': self.created_at,
            'status': self.status
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'DDSProposal':
        """Create proposal from dictionary"""
        return DDSProposal(
            id=data['id'],
            project=data['project'],
            title=data['title'],
            description=data['description'],
            created_at=data['created_at'],
            status=data['status']
        )
