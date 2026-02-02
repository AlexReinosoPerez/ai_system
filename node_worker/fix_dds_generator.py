"""
Fix DDS Generator - Creates code_fix DDS proposals

Responsibility: Generate code_fix DDS from failure information.
NO execution, NO approval, NO side effects beyond DDS creation.
"""

from datetime import datetime
from typing import Dict


class FixDDSGenerator:
    """
    Generates code_fix DDS proposals from failure information.
    
    Pure transformation logic - deterministic output.
    """
    
    def generate_fix_dds(
        self,
        failed_dds: Dict,
        failure_info: Dict
    ) -> Dict:
        """
        Generate a code_fix DDS from failed DDS and failure info
        
        Args:
            failed_dds: The DDS that failed (from dds.json)
            failure_info: Failure information from FailureAnalyzer
        
        Returns:
            Dict with complete code_fix DDS structure
        """
        # Generate unique ID
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        fix_id = f"DDS-FIX-{timestamp}"
        
        # Truncate and sanitize error message
        error_message = self._sanitize_error(
            failure_info.get('error_message', 'Unknown error')
        )
        
        # Create conservative instructions
        instructions = self._generate_instructions(
            failed_dds.get('title', failed_dds.get('goal', 'Unknown')),
            error_message
        )
        
        # Inherit and restrict constraints
        original_constraints = failed_dds.get('constraints', {})
        fix_constraints = {
            'max_files_changed': min(
                original_constraints.get('max_files_changed', 5),
                3  # Hard limit for code_fix
            ),
            'no_new_dependencies': True,  # Always enforced
            'no_refactor': True  # Always enforced
        }
        
        # Build code_fix DDS
        code_fix_dds = {
            'id': fix_id,
            'version': 2,
            'type': 'code_fix',
            'project': failed_dds.get('project', 'unknown'),
            'goal': f"Fix execution failure in {failure_info['dds_id']}: {error_message[:100]}",
            'instructions': instructions,
            'allowed_paths': failed_dds.get('allowed_paths', ['src/', 'tests/']),
            'tool': failed_dds.get('tool', 'aider'),
            'constraints': fix_constraints,
            'status': 'proposed',
            'source_dds': failure_info['dds_id'],
            'error_context': {
                'original_dds': failure_info['dds_id'],
                'error_message': error_message,
                'failed_at': failure_info['failed_at']
            }
        }
        
        return code_fix_dds
    
    def _sanitize_error(self, error_message: str) -> str:
        """Truncate and sanitize error message"""
        # Truncate to 500 chars
        truncated = error_message[:500]
        
        # Remove null bytes and normalize newlines
        sanitized = truncated.replace('\x00', '').replace('\r', '\n')
        
        return sanitized
    
    def _generate_instructions(self, original_goal: str, error_message: str) -> list:
        """Generate conservative fix instructions"""
        # Extract first line of error for focused instruction
        error_summary = error_message.split('\n')[0][:100]
        
        return [
            f"Analyze error: {error_summary}",
            "Identify root cause in affected files",
            "Apply minimal fix to resolve error",
            "Verify fix doesn't break existing tests"
        ]
