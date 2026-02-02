"""
Aider Runner - Real Aider tool execution (v2.1)

Executes Aider within scoped workspace without commits
"""

import subprocess
from typing import List, Dict


def run_aider(workspace_path: str, allowed_paths: List[str], prompt: str) -> Dict[str, any]:
    """
    Execute Aider within scoped workspace.
    
    Args:
        workspace_path: Absolute path to isolated workspace directory (_scoped/)
        allowed_paths: List of paths where Aider is allowed to operate
        prompt: Instructions for Aider to execute
        
    Returns:
        dict: Execution result with keys:
            - returncode: int (0 = success)
            - stdout: str (command output)
            - stderr: str (error output)
            - success: bool (returncode == 0)
    """
    # Build Aider command
    # Format: aider --no-auto-commit --yes --message "prompt" <allowed_paths>
    command = [
        'aider',
        '--no-auto-commit',  # Prevent automatic commits
        '--yes',              # Auto-accept confirmations
        '--message', prompt   # Pass the prompt as message
    ]
    
    # Add allowed paths as arguments
    command.extend(allowed_paths)
    
    # Execute Aider in the scoped workspace
    try:
        result = subprocess.run(
            command,
            cwd=workspace_path,  # Execute in _scoped/ directory
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        return {
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
    except subprocess.TimeoutExpired as e:
        return {
            'returncode': -1,
            'stdout': e.stdout.decode() if e.stdout else '',
            'stderr': f'Timeout after 300 seconds: {str(e)}',
            'success': False
        }
        
    except FileNotFoundError:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': 'Aider command not found. Please install aider: pip install aider-chat',
            'success': False
        }
        
    except Exception as e:
        return {
            'returncode': -1,
            'stdout': '',
            'stderr': f'Unexpected error executing Aider: {str(e)}',
            'success': False
        }
