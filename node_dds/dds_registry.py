"""
DDS Registry - Manages DDS proposals with JSON persistence
"""

import json
import os
from datetime import datetime
from typing import List
from node_dds.dds_proposal import DDSProposal
from shared.logger import setup_logger

logger = setup_logger(__name__)


class DDSRegistryError(Exception):
    """Raised when DDS registry operations fail"""
    pass


class DDSRegistry:
    """Manages DDS proposals with JSON persistence"""
    
    DDS_FILE = "node_dds/dds.json"
    
    def __init__(self):
        """Initialize DDS registry"""
        logger.info("DDS registry initialized")
    
    def _load_proposals(self) -> List[DDSProposal]:
        """Load proposals from JSON file"""
        if not os.path.exists(self.DDS_FILE):
            logger.warning(f"DDS file not found: {self.DDS_FILE}")
            return []
        
        try:
            with open(self.DDS_FILE, 'r') as f:
                data = json.load(f)
            
            proposals_data = data.get('proposals', [])
            proposals = [DDSProposal.from_dict(p) for p in proposals_data]
            logger.info(f"Loaded {len(proposals)} proposals")
            return proposals
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse dds.json: {e}")
            raise DDSRegistryError(f"Invalid JSON format: {str(e)}") from e
        except Exception as e:
            logger.error(f"Failed to load proposals: {e}")
            raise DDSRegistryError(f"Error loading proposals: {str(e)}") from e
    
    def _save_proposals(self, proposals: List[DDSProposal]):
        """Save proposals to JSON file"""
        try:
            data = {
                'proposals': [p.to_dict() for p in proposals]
            }
            
            os.makedirs(os.path.dirname(self.DDS_FILE), exist_ok=True)
            
            with open(self.DDS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved {len(proposals)} proposals")
            
        except Exception as e:
            logger.error(f"Failed to save proposals: {e}")
            raise DDSRegistryError(f"Error saving proposals: {str(e)}") from e
    
    def list_proposals(self) -> List[DDSProposal]:
        """
        List all proposals
        
        Returns:
            List of proposals
        """
        return self._load_proposals()
    
    def list_proposed(self) -> List[DDSProposal]:
        """
        List proposals with status='proposed'
        
        Returns:
            List of proposed DDSs
        """
        proposals = self._load_proposals()
        return [p for p in proposals if p.status == 'proposed']
    
    def add_proposal(self, proposal: DDSProposal):
        """
        Add new proposal
        
        Args:
            proposal: DDSProposal to add
        """
        proposals = self._load_proposals()
        
        # Generate ID if not set
        if not proposal.id:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            proposal.id = f"DDS-{timestamp}"
        
        proposals.append(proposal)
        self._save_proposals(proposals)
        
        logger.info(f"Added proposal: {proposal.id}")
    
    def approve(self, proposal_id: str) -> bool:
        """
        Approve a proposal
        
        Args:
            proposal_id: Proposal ID to approve
            
        Returns:
            True if found and approved, False otherwise
        """
        proposals = self._load_proposals()
        
        for proposal in proposals:
            if proposal.id == proposal_id:
                proposal.status = 'approved'
                self._save_proposals(proposals)
                logger.info(f"Approved proposal: {proposal_id}")
                return True
        
        logger.warning(f"Proposal not found for approval: {proposal_id}")
        return False
    
    def reject(self, proposal_id: str) -> bool:
        """
        Reject a proposal
        
        Args:
            proposal_id: Proposal ID to reject
            
        Returns:
            True if found and rejected, False otherwise
        """
        proposals = self._load_proposals()
        
        for proposal in proposals:
            if proposal.id == proposal_id:
                proposal.status = 'rejected'
                self._save_proposals(proposals)
                logger.info(f"Rejected proposal: {proposal_id}")
                return True
        
        logger.warning(f"Proposal not found for rejection: {proposal_id}")
        return False
