"""
Programmer - DDS execution engine with noop actions
"""

import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from node_programmer.execution_report import ExecutionReport
from node_programmer.external_tools.aider_runner import run_aider
from shared.logger import setup_logger

logger = setup_logger(__name__)


class ProgrammerError(Exception):
    """Raised when programmer operations fail"""
    pass


class Programmer:
    """Executes approved DDS proposals with controlled actions"""
    
    REPORTS_FILE = "node_programmer/reports.json"
    SANDBOX_DIR = "node_programmer/sandbox"
    WORKSPACES_DIR = "node_programmer/workspaces"
    DDS_FILE = "node_dds/dds.json"
    
    def __init__(self):
        """Initialize programmer"""
        logger.info("Programmer initialized")
        os.makedirs(self.SANDBOX_DIR, exist_ok=True)
    
    def _validate_sandbox_path(self, relative_path: str) -> Path:
        """
        Validate that a path is safe for sandbox operations
        
        Args:
            relative_path: Path string to validate (must be relative)
            
        Returns:
            Absolute Path object inside sandbox
            
        Raises:
            ProgrammerError: If path is unsafe (absolute, contains .., outside sandbox)
        """
        # Check for absolute path
        if os.path.isabs(relative_path):
            raise ProgrammerError(f"Absolute paths not allowed: {relative_path}")
        
        # Check for path traversal
        if '..' in relative_path:
            raise ProgrammerError(f"Path traversal not allowed: {relative_path}")
        
        # Resolve to absolute path
        sandbox_abs = Path(self.SANDBOX_DIR).resolve()
        target_abs = (sandbox_abs / relative_path).resolve()
        
        # Verify target is inside sandbox
        try:
            target_abs.relative_to(sandbox_abs)
        except ValueError:
            raise ProgrammerError(f"Path outside sandbox: {relative_path}")
        
        logger.info(f"Validated sandbox path: {relative_path} -> {target_abs}")
        return target_abs
    
    def _validate_allowed_paths(self, target_path: Path, allowed_paths: list) -> bool:
        """
        Validate that target path is within allowed paths scope
        
        Args:
            target_path: Absolute Path to validate
            allowed_paths: List of relative paths from DDS allowed_paths field
            
        Returns:
            True if path is allowed
            
        Raises:
            ProgrammerError: If allowed_paths missing or target not in scope
        """
        if not allowed_paths:
            raise ProgrammerError("DDS missing required field: allowed_paths")
        
        sandbox_abs = Path(self.SANDBOX_DIR).resolve()
        
        for allowed in allowed_paths:
            allowed_abs = (sandbox_abs / allowed).resolve()
            
            # Check if target is the allowed path or inside it
            try:
                target_path.relative_to(allowed_abs)
                logger.info(f"Path allowed: {target_path} within {allowed}")
                return True
            except ValueError:
                continue
        
        raise ProgrammerError("Target path not allowed by DDS")
    
    def _build_aider_prompt(self, dds: dict) -> str:
        """
        Build Aider prompt from DDS v2 specification
        
        Args:
            dds: DDS proposal dictionary
            
        Returns:
            Formatted prompt string for Aider
            
        Raises:
            ProgrammerError: If required fields are missing
        """
        logger.info(f"Building Aider prompt for DDS: {dds.get('id')}")
        
        # Extract required fields
        goal = dds.get('goal')
        if not goal:
            raise ProgrammerError("Cannot build prompt: missing goal")
        
        instructions = dds.get('instructions')
        if not instructions or not isinstance(instructions, list):
            raise ProgrammerError("Cannot build prompt: missing or invalid instructions")
        
        constraints = dds.get('constraints')
        if not constraints or not isinstance(constraints, dict):
            raise ProgrammerError("Cannot build prompt: missing or invalid constraints")
        
        # Build prompt
        prompt_parts = []
        
        # Goal section
        prompt_parts.append("GOAL:")
        prompt_parts.append(goal)
        prompt_parts.append("")
        
        # Instructions section
        prompt_parts.append("INSTRUCTIONS:")
        for instruction in instructions:
            prompt_parts.append(f"- {instruction}")
        prompt_parts.append("")
        
        # Constraints section
        prompt_parts.append("CONSTRAINTS:")
        
        max_files = constraints.get('max_files_changed', constraints.get('max_files', 'not specified'))
        prompt_parts.append(f"- Max files changed: {max_files}")
        
        no_deps = constraints.get('no_new_dependencies', False)
        prompt_parts.append(f"- No new dependencies: {str(no_deps).lower()}")
        
        no_refactor = constraints.get('no_refactor', False)
        prompt_parts.append(f"- No refactor: {str(no_refactor).lower()}")
        prompt_parts.append("")
        
        # Rules section
        prompt_parts.append("RULES:")
        prompt_parts.append("- Only modify files in allowed paths")
        prompt_parts.append("- Do not commit changes")
        prompt_parts.append("- Stop after completing instructions")
        
        prompt = "\n".join(prompt_parts)
        logger.info(f"Built prompt ({len(prompt)} chars) for DDS: {dds.get('id')}")
        
        return prompt
    
    def _save_execution_report(self, report: ExecutionReport) -> None:
        """
        Save execution report to reports.json (append-only)
        
        Args:
            report: ExecutionReport to persist
        """
        reports_file = Path(self.REPORTS_FILE)
        
        # Load existing reports
        if reports_file.exists():
            with open(reports_file, 'r') as f:
                data = json.load(f)
                executions = data.get('executions', [])
        else:
            executions = []
        
        # Append new report
        executions.append(report.to_dict())
        
        # Save back
        reports_file.parent.mkdir(parents=True, exist_ok=True)
        with open(reports_file, 'w') as f:
            json.dump({'executions': executions}, f, indent=2)
        
        logger.info(f"Saved execution report for DDS: {report.dds_id}")
    
    def _mark_dds_executed(self, dds_id: str, execution_status: str, executed_at: str, notes: str) -> None:
        """
        Mark DDS as executed in dds.json
        
        Args:
            dds_id: DDS identifier
            execution_status: 'success' or 'failed'
            executed_at: Timestamp of execution
            notes: Summary of execution result
        """
        dds_file = Path(self.DDS_FILE)
        
        if not dds_file.exists():
            logger.warning(f"DDS file not found: {dds_file}")
            return
        
        # Load DDS file
        with open(dds_file, 'r') as f:
            data = json.load(f)
        
        # Find and update DDS
        proposals = data.get('proposals', [])
        for proposal in proposals:
            if proposal.get('id') == dds_id:
                proposal['last_execution'] = {
                    'status': execution_status,
                    'executed_at': executed_at,
                    'notes': notes
                }
                break
        
        # Save back
        with open(dds_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Marked DDS as executed: {dds_id} -> {execution_status}")
    
    def _check_already_executed(self, dds_id: str) -> bool:
        """
        Check if DDS has already been executed successfully
        
        Args:
            dds_id: DDS identifier
            
        Returns:
            True if DDS already executed successfully
        """
        dds_file = Path(self.DDS_FILE)
        
        if not dds_file.exists():
            return False
        
        with open(dds_file, 'r') as f:
            data = json.load(f)
        
        proposals = data.get('proposals', [])
        for proposal in proposals:
            if proposal.get('id') == dds_id:
                last_exec = proposal.get('last_execution', {})
                return last_exec.get('status') == 'success'
        
        return False
    
    def _build_user_summary(self, report: ExecutionReport, created: List[str], modified: List[str], deleted: List[str], constraints_ok: bool, violations: List[str]) -> str:
        """
        Build clear user-facing summary of execution
        
        Args:
            report: Execution report
            created: Created files
            modified: Modified files
            deleted: Deleted files
            constraints_ok: Whether constraints validated
            violations: List of constraint violations
            
        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"DDS Execution Report: {report.dds_id}")
        lines.append("=" * 60)
        lines.append(f"Status: {report.status.upper()}")
        lines.append(f"Executed at: {report.executed_at}")
        lines.append("")
        lines.append("Changes Detected:")
        lines.append(f"  - Created: {len(created)} files")
        lines.append(f"  - Modified: {len(modified)} files")
        lines.append(f"  - Deleted: {len(deleted)} files")
        lines.append("")
        lines.append(f"Constraints Validation: {'✓ PASSED' if constraints_ok else '✗ FAILED'}")
        
        if violations:
            lines.append("Violations:")
            for violation in violations:
                lines.append(f"  - {violation}")
        
        lines.append("")
        lines.append(f"Notes: {report.notes}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _create_workspace_snapshot(self, workspace_path: Path) -> Dict[str, str]:
        """
        Create snapshot of workspace files (path -> hash)
        
        Args:
            workspace_path: Path to workspace directory
            
        Returns:
            Dictionary mapping relative paths to file content hashes
        """
        snapshot = {}
        
        for file_path in workspace_path.rglob('*'):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(workspace_path))
                
                try:
                    with open(file_path, 'rb') as f:
                        content_hash = hashlib.md5(f.read()).hexdigest()
                    snapshot[relative_path] = content_hash
                except Exception as e:
                    logger.warning(f"Failed to hash file {relative_path}: {e}")
        
        logger.info(f"Created snapshot with {len(snapshot)} files")
        return snapshot
    
    def _detect_changes(self, workspace_path: Path, before_snapshot: Dict[str, str]) -> Tuple[List[str], List[str], List[str]]:
        """
        Detect file changes by comparing current state with snapshot
        
        Args:
            workspace_path: Path to workspace directory
            before_snapshot: Snapshot created before execution
            
        Returns:
            Tuple of (created_files, modified_files, deleted_files)
        """
        after_snapshot = self._create_workspace_snapshot(workspace_path)
        
        created = []
        modified = []
        deleted = []
        
        # Find created and modified files
        for path, hash_after in after_snapshot.items():
            if path not in before_snapshot:
                created.append(path)
            elif before_snapshot[path] != hash_after:
                modified.append(path)
        
        # Find deleted files
        for path in before_snapshot:
            if path not in after_snapshot:
                deleted.append(path)
        
        logger.info(f"Detected changes: {len(created)} created, {len(modified)} modified, {len(deleted)} deleted")
        return created, modified, deleted
    
    def _validate_constraints(self, dds: dict, created: List[str], modified: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate DDS constraints against detected changes
        
        Args:
            dds: DDS proposal dictionary
            created: List of created file paths
            modified: List of modified file paths
            
        Returns:
            Tuple of (constraints_ok, violations)
        """
        violations = []
        constraints = dds.get('constraints', {})
        
        # Check max_files_changed
        max_files = constraints.get('max_files_changed', constraints.get('max_files'))
        if max_files is not None:
            total_changed = len(created) + len(modified)
            if total_changed > max_files:
                violations.append(f"Max files changed exceeded: {total_changed} > {max_files}")
        
        # Check no_new_dependencies (heuristic: look for package.json, requirements.txt, etc.)
        no_deps = constraints.get('no_new_dependencies', False)
        if no_deps:
            dependency_files = ['package.json', 'requirements.txt', 'Pipfile', 'pyproject.toml', 'Cargo.toml', 'go.mod']
            for file in created + modified:
                if any(dep_file in file for dep_file in dependency_files):
                    violations.append(f"Dependency file modified: {file}")
        
        # Check no_refactor (heuristic: too many files changed suggests refactoring)
        no_refactor = constraints.get('no_refactor', False)
        if no_refactor:
            total_changed = len(created) + len(modified)
            if total_changed > 3:  # Heuristic: > 3 files suggests refactoring
                violations.append(f"Possible refactoring detected: {total_changed} files changed")
        
        constraints_ok = len(violations) == 0
        logger.info(f"Constraint validation: {constraints_ok} (violations: {len(violations)})")
        
        return constraints_ok, violations
    
    def _validate_dds_v2(self, dds: dict) -> None:
        """
        Validate DDS v2 structure and contract
        
        Args:
            dds: DDS proposal dictionary
            
        Raises:
            ProgrammerError: If validation fails
        """
        logger.info(f"Validating DDS v2: {dds.get('id')}")
        
        # Validate version
        version = dds.get('version')
        if version != 2:
            raise ProgrammerError(f"Invalid version: expected 2, got {version}")
        
        # Validate type
        dds_type = dds.get('type')
        if dds_type != 'code_change':
            raise ProgrammerError(f"Invalid type: expected 'code_change', got {dds_type}")
        
        # Validate project
        project = dds.get('project')
        if not project:
            raise ProgrammerError("Missing required field: project")
        
        # Validate goal
        goal = dds.get('goal')
        if not goal or not isinstance(goal, str) or not goal.strip():
            raise ProgrammerError("Missing or invalid required field: goal (must be non-empty string)")
        
        # Validate instructions
        instructions = dds.get('instructions')
        if not instructions or not isinstance(instructions, list) or len(instructions) == 0:
            raise ProgrammerError("Missing or invalid required field: instructions (must be non-empty list)")
        
        # Validate allowed_paths
        allowed_paths = dds.get('allowed_paths')
        if not allowed_paths or not isinstance(allowed_paths, list) or len(allowed_paths) == 0:
            raise ProgrammerError("Missing or invalid required field: allowed_paths (must be non-empty list)")
        
        # Validate tool
        tool = dds.get('tool')
        if tool != 'aider':
            raise ProgrammerError(f"Invalid tool: expected 'aider', got {tool}")
        
        # Validate constraints
        constraints = dds.get('constraints')
        if not constraints or not isinstance(constraints, dict):
            raise ProgrammerError("Missing or invalid required field: constraints (must be dict)")
        
        # Validate status
        status = dds.get('status')
        if status != 'approved':
            raise ProgrammerError(f"DDS not approved: status is '{status}'")
        
        logger.info(f"DDS v2 validation passed: {dds.get('id')}")
    
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
            
            # Validate allowed_paths
            target_path = Path(filepath).resolve()
            allowed_paths = dds_found.get('allowed_paths')
            self._validate_allowed_paths(target_path, allowed_paths)
            
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
    
    def execute_touch_file(self, dds_id: str) -> ExecutionReport:
        """
        Execute touch_file action for DDS proposal
        
        Args:
            dds_id: DDS proposal ID to execute
            
        Returns:
            ExecutionReport with execution details
            
        Raises:
            ProgrammerError: If execution fails
        """
        logger.info(f"Executing touch_file for DDS: {dds_id}")
        
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
        
        # Validate required fields
        path = dds_found.get('path')
        content = dds_found.get('content')
        
        if not path:
            raise ProgrammerError(f"DDS {dds_id} missing required field: path")
        
        if content is None:  # Allow empty string
            raise ProgrammerError(f"DDS {dds_id} missing required field: content")
        
        # Execute touch_file action
        try:
            # Validate and resolve path
            target_path = self._validate_sandbox_path(path)
            
            # Validate allowed_paths
            allowed_paths = dds_found.get('allowed_paths')
            self._validate_allowed_paths(target_path, allowed_paths)
            
            # Check if file exists
            file_existed = target_path.exists()
            
            # Create parent directories if needed
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            target_path.write_text(content, encoding='utf-8')
            
            # Calculate bytes written
            bytes_written = len(content.encode('utf-8'))
            
            result = "overwritten" if file_existed else "created"
            executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"File {result}: {target_path} ({bytes_written} bytes)")
            
            # Create execution report
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='touch_file',
                status='success',
                executed_at=executed_at,
                notes=f"File {result}: {path} ({bytes_written} bytes written)"
            )
            
            # Save report
            self._save_report(report)
            
            logger.info(f"Successfully executed DDS {dds_id}")
            return report
            
        except ProgrammerError:
            # Re-raise validation errors
            raise
            
        except Exception as e:
            logger.error(f"Execution failed for DDS {dds_id}: {e}")
            
            # Create failure report
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='touch_file',
                status='failed',
                executed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                notes=f"Execution failed: {str(e)}"
            )
            
            self._save_report(report)
            raise ProgrammerError(f"Execution failed: {str(e)}") from e
    
    def execute_code_change(self, dds_id: str) -> ExecutionReport:
        """
        Execute code_change action for DDS v2 proposal (PHASE 2-8)
        
        Args:
            dds_id: DDS proposal ID to execute
            
        Returns:
            ExecutionReport with validation status
            
        Raises:
            ProgrammerError: If validation fails or already executed
        """
        logger.info(f"Executing code_change for DDS: {dds_id}")
        
        # PHASE 8: Check if already executed successfully
        if self._check_already_executed(dds_id):
            error_msg = f"DDS already executed successfully: {dds_id}"
            logger.error(error_msg)
            
            execution_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='code_change',
                status='failed',
                executed_at=execution_time,
                notes=error_msg
            )
            
            self._save_execution_report(report)
            raise ProgrammerError(error_msg)
        
        # Check if already executed (old method for backwards compatibility)
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
        
        # Validate DDS v2 structure
        try:
            self._validate_dds_v2(dds_found)
            
            # PHASE 3: Create ephemeral workspace
            project = dds_found.get('project')
            workspace_path = Path(self.WORKSPACES_DIR) / dds_id
            
            # Create workspace directory
            workspace_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created workspace: {workspace_path}")
            
            # Determine project source path (assuming projects are in root or specific location)
            # For this implementation, we'll use a mock project structure
            # In production, this would map to actual project repositories
            project_source = Path(project)
            
            if not project_source.exists():
                # Try common locations
                possible_sources = [
                    Path(f"../{project}"),
                    Path(f"../../{project}"),
                    Path(f"projects/{project}")
                ]
                
                for source in possible_sources:
                    if source.exists():
                        project_source = source
                        break
            
            # Copy project files to workspace
            if project_source.exists() and project_source.is_dir():
                # Copy contents to workspace
                for item in project_source.iterdir():
                    if item.is_dir():
                        shutil.copytree(item, workspace_path / item.name, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, workspace_path)
                
                logger.info(f"Copied project '{project}' to workspace: {workspace_path}")
                file_count = len(list(workspace_path.rglob('*')))
                
                # PHASE 4: Create scoped workspace with allowed_paths only
                allowed_paths = dds_found.get('allowed_paths', [])
                scoped_path = workspace_path / '_scoped'
                scoped_path.mkdir(exist_ok=True)
                logger.info(f"Creating scoped workspace: {scoped_path}")
                
                # Validate and copy allowed paths
                for allowed in allowed_paths:
                    # Validate path
                    source_path = workspace_path / allowed
                    
                    # Check if path exists
                    if not source_path.exists():
                        raise ProgrammerError(f"Allowed path does not exist in workspace: {allowed}")
                    
                    # Ensure it's within workspace (security check)
                    try:
                        source_path.resolve().relative_to(workspace_path.resolve())
                    except ValueError:
                        raise ProgrammerError(f"Allowed path escapes workspace: {allowed}")
                    
                    # Copy to scoped workspace
                    target_path = scoped_path / allowed
                    
                    if source_path.is_dir():
                        # Copy directory with all contents
                        shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                        logger.info(f"Copied directory to scoped workspace: {allowed}")
                    else:
                        # Copy individual file
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source_path, target_path)
                        logger.info(f"Copied file to scoped workspace: {allowed}")
                
                scoped_count = len(list(scoped_path.rglob('*')))
                
                # PHASE 5: Build Aider prompt
                prompt = self._build_aider_prompt(dds_found)
                logger.info(f"Aider prompt built successfully")
                
                # Log prompt preview (first 200 chars)
                prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
                logger.debug(f"Prompt preview: {prompt_preview}")
                
                # PHASE 7: Create workspace snapshot before execution
                before_snapshot = self._create_workspace_snapshot(scoped_path)
                
                # PHASE 6: Invoke external tool (mock)
                try:
                    logger.info(f"Invoking Aider for DDS: {dds_id}")
                    logger.info(f"Workspace: {scoped_path}")
                    logger.info(f"Allowed paths: {allowed_paths}")
                    
                    result = run_aider(
                        workspace_path=str(scoped_path),
                        allowed_paths=allowed_paths,
                        prompt=prompt
                    )
                    
                    # PHASE 7: Post-execution analysis
                    logger.info("Analyzing execution results")
                    
                    created, modified, deleted = self._detect_changes(scoped_path, before_snapshot)
                    constraints_ok, violations = self._validate_constraints(dds_found, created, modified)
                    
                    all_changed = created + modified
                    
                    # Determine final status
                    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if constraints_ok and len(all_changed) > 0:
                        status = 'success'
                        notes = f"Execution completed. Files changed: {len(all_changed)} ({len(created)} created, {len(modified)} modified). Constraints: OK."
                    elif not constraints_ok:
                        status = 'failed'
                        notes = f"Constraint violations: {', '.join(violations)}. Files changed: {len(all_changed)}"
                    else:
                        status = 'success'
                        notes = f"Execution completed. No files changed."
                    
                    report = ExecutionReport(
                        dds_id=dds_id,
                        action_type='code_change',
                        status=status,
                        executed_at=executed_at,
                        notes=notes
                    )
                    
                    # PHASE 8: Persist report and mark DDS executed
                    self._save_execution_report(report)
                    self._mark_dds_executed(dds_id, status, executed_at, notes)
                    
                    # Build user summary
                    summary = self._build_user_summary(report, created, modified, deleted, constraints_ok, violations)
                    logger.info(f"\n{summary}")
                    
                    logger.info(f"DDS v2 executed successfully: {dds_id}")
                    return report
                    
                except NotImplementedError as e:
                    # Expected in PHASE 6/7: aider_runner not yet implemented
                    # Simulate post-execution analysis with no changes
                    logger.info(f"Aider runner not implemented (expected): {e}")
                    logger.info("Simulating post-execution analysis (no changes expected)")
                    
                    created, modified, deleted = self._detect_changes(scoped_path, before_snapshot)
                    constraints_ok, violations = self._validate_constraints(dds_found, created, modified)
                    
                    all_changed = created + modified
                    
                    executed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    report = ExecutionReport(
                        dds_id=dds_id,
                        action_type='code_change',
                        status='failed',
                        executed_at=executed_at,
                        notes=f'External tool not implemented. Workspace prepared at: {scoped_path}. Post-execution analysis: {len(all_changed)} files changed'
                    )
                    
                    # PHASE 8: Persist report and mark DDS executed (as failed)
                    self._save_execution_report(report)
                    self._mark_dds_executed(dds_id, 'failed', executed_at, report.notes)
                    
                    # Build user summary
                    summary = self._build_user_summary(report, created, modified, deleted, constraints_ok, violations)
                    logger.info(f"\n{summary}")
                    
                    logger.info(f"DDS v2 workspace prepared, tool invocation attempted: {dds_id}")
                    return report
                    
            else:
                raise ProgrammerError(f"Project source not found: {project}")
            
        except ProgrammerError as e:
            logger.error(f"DDS v2 execution failed: {e}")
            
            # Create failure report
            execution_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='code_change',
                status='failed',
                executed_at=execution_time,
                notes=f"Execution failed: {str(e)}"
            )
            
            # PHASE 8: Persist report and mark DDS executed (as failed)
            self._save_execution_report(report)
            self._mark_dds_executed(dds_id, 'failed', execution_time, report.notes)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during workspace creation: {e}")
            
            # Create failure report
            execution_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            report = ExecutionReport(
                dds_id=dds_id,
                action_type='code_change',
                status='failed',
                executed_at=execution_time,
                notes=f"Workspace creation failed: {str(e)}"
            )
            
            # PHASE 8: Persist report and mark DDS executed (as failed)
            self._save_execution_report(report)
            self._mark_dds_executed(dds_id, 'failed', execution_time, report.notes)
            raise ProgrammerError(f"Workspace creation failed: {str(e)}") from e
    
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
