"""
Reactive Worker - Monitors failures and proposes corrections

Responsibility: Orchestrate failure detection and correction proposal.
NO execution, NO approval, NO autonomous retry.
"""

from shared.logger import setup_logger
from node_dds.dds_registry import DDSRegistry, DDSRegistryError
from node_dds.dds_proposal import DDSProposal
from node_worker.failure_analyzer import FailureAnalyzer
from node_worker.fix_dds_generator import FixDDSGenerator
from datetime import datetime
from typing import Dict

logger = setup_logger(__name__)


class ReactiveWorker:
    """
    Reactive Worker v1: Detects failures and generates correction proposals.
    
    Stop-on-failure semantics: Halts after first proposal generation.
    """
    
    def __init__(self):
        """Initialize worker components"""
        self.failure_analyzer = FailureAnalyzer()
        self.fix_generator = FixDDSGenerator()
        self.dds_registry = DDSRegistry()
        logger.info("Reactive Worker initialized")
    
    def run(self) -> Dict:
        """
        Execute worker: detect failures and propose corrections
        
        Returns:
            Dict with execution summary:
            {
                'status': 'completed' | 'no_failures' | 'stopped_on_error',
                'proposals_generated': int,
                'failed_dds_id': str | None,
                'message': str
            }
        """
        logger.info("=== Reactive Worker execution started ===")
        
        try:
            # Phase 1: Detect failure
            failure_info = self.failure_analyzer.get_latest_failure()
            
            if not failure_info:
                logger.info("No failures detected")
                return {
                    'status': 'no_failures',
                    'proposals_generated': 0,
                    'failed_dds_id': None,
                    'message': 'No failures detected in reports.json'
                }
            
            failed_dds_id = failure_info['dds_id']
            logger.info(f"Failure detected: {failed_dds_id}")
            
            # Phase 2: Check for existing code_fix
            if self._code_fix_exists(failed_dds_id):
                logger.info(f"Code fix already exists for {failed_dds_id}")
                return {
                    'status': 'no_failures',
                    'proposals_generated': 0,
                    'failed_dds_id': failed_dds_id,
                    'message': f'Code fix already proposed for {failed_dds_id}'
                }
            
            # Phase 3: Load failed DDS
            failed_dds = self._get_dds_by_id(failed_dds_id)
            
            if not failed_dds:
                logger.warning(f"Failed DDS not found in registry: {failed_dds_id}")
                return {
                    'status': 'stopped_on_error',
                    'proposals_generated': 0,
                    'failed_dds_id': failed_dds_id,
                    'message': f'Failed DDS not found: {failed_dds_id}'
                }
            
            # Phase 4: Generate code_fix DDS
            code_fix_dds = self.fix_generator.generate_fix_dds(
                failed_dds,
                failure_info
            )
            
            logger.info(f"Generated code_fix DDS: {code_fix_dds['id']}")
            
            # Phase 5: Persist code_fix DDS
            self._save_code_fix(code_fix_dds)
            
            # Phase 6: Mark failure as processed so it won't be re-proposed
            self.failure_analyzer.mark_processed(failed_dds_id)
            
            logger.info(f"=== Reactive Worker completed: 1 proposal generated ===")
            
            return {
                'status': 'completed',
                'proposals_generated': 1,
                'failed_dds_id': failed_dds_id,
                'message': f"Code fix proposed: {code_fix_dds['id']}"
            }
            
        except Exception as e:
            logger.error(f"Worker error: {e}")
            return {
                'status': 'stopped_on_error',
                'proposals_generated': 0,
                'failed_dds_id': None,
                'message': f'Error: {str(e)}'
            }
    
    def _code_fix_exists(self, source_dds_id: str) -> bool:
        """Check if code_fix already exists for given DDS.
        
        Uses the persisted source_dds field (primary) and
        title pattern match (fallback) to detect duplicates.
        """
        try:
            proposals = self.dds_registry.list_proposals()
            
            for proposal in proposals:
                # Primary: check persisted source_dds field
                if (proposal.source_dds == source_dds_id and
                    proposal.dds_type == 'code_fix'):
                    return True
                # Fallback: title contains source DDS ID
                # (covers fixes created before extended fields were persisted)
                if (proposal.dds_type == 'code_fix' and
                    source_dds_id in (proposal.title or '')):
                    return True
            
            return False
            
        except DDSRegistryError:
            return False
    
    def _get_dds_by_id(self, dds_id: str) -> Dict:
        """Get DDS by ID from registry"""
        try:
            proposals = self.dds_registry.list_proposals()
            
            for proposal in proposals:
                if proposal.id == dds_id:
                    return proposal.to_dict()
            
            return None
            
        except DDSRegistryError:
            return None
    
    def _save_code_fix(self, code_fix_dds: Dict):
        """Save code_fix DDS to registry with all extended fields."""
        proposal = DDSProposal(
            id=code_fix_dds['id'],
            project=code_fix_dds['project'],
            title=code_fix_dds['goal'],
            description=str(code_fix_dds['instructions']),
            created_at=datetime.now().isoformat(),
            status=code_fix_dds['status'],
            # Execution fields — needed by Programmer
            version=code_fix_dds.get('version'),
            goal=code_fix_dds.get('goal'),
            instructions=code_fix_dds.get('instructions'),
            tool=code_fix_dds.get('tool'),
            # Extended fields — critical for human review
            dds_type=code_fix_dds.get('type'),
            source_dds=code_fix_dds.get('source_dds'),
            error_context=code_fix_dds.get('error_context'),
            constraints=code_fix_dds.get('constraints'),
            allowed_paths=code_fix_dds.get('allowed_paths'),
        )
        
        self.dds_registry.add_proposal(proposal)
        logger.info(f"Code fix DDS saved: {code_fix_dds['id']}")
