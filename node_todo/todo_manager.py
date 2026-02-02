"""
TodoManager - Gestión del ciclo de vida de tareas

Responsabilidad: CRUD de tareas y manejo de estados.
NO aprueba ni ejecuta DDS. Solo gestiona tareas de alto nivel.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from shared.logger import get_logger

logger = get_logger(__name__)


class TodoManager:
    """
    Gestor de tareas (ToDo) del sistema ai_system.
    
    Permite crear, listar, actualizar y vincular tareas con DDS.
    Todas las operaciones se persisten en todos.json.
    """
    
    # Estados válidos y transiciones permitidas
    VALID_STATES = {
        'pending',           # Tarea creada, sin DDS asociado
        'draft_generated',   # DDS draft creado, esperando aprobación
        'approved',          # DDS aprobado por humano (no ejecutado)
        'completed',         # DDS ejecutado con éxito
        'failed',            # DDS ejecutado con error
        'cancelled'          # Tarea cancelada por humano
    }
    
    STATE_TRANSITIONS = {
        'pending': {'draft_generated', 'cancelled'},
        'draft_generated': {'approved', 'pending', 'cancelled'},
        'approved': {'completed', 'failed', 'cancelled'},
        'completed': set(),  # Estado final
        'failed': {'pending', 'cancelled'},
        'cancelled': set()   # Estado final
    }
    
    def __init__(self, todos_file: Optional[str] = None):
        """
        Inicializa el gestor de tareas.
        
        Args:
            todos_file: Ruta al archivo todos.json. Si es None, usa ubicación por defecto.
        """
        if todos_file is None:
            self.todos_file = Path(__file__).parent / 'todos.json'
        else:
            self.todos_file = Path(todos_file)
        
        self._ensure_todos_file_exists()
        logger.info(f"TodoManager inicializado con archivo: {self.todos_file}")
    
    def _ensure_todos_file_exists(self) -> None:
        """Crea el archivo todos.json si no existe."""
        if not self.todos_file.exists():
            initial_data = {"todos": []}
            with open(self.todos_file, 'w') as f:
                json.dump(initial_data, f, indent=2)
            logger.info(f"Archivo todos.json creado: {self.todos_file}")
    
    def _load_todos(self) -> Dict:
        """Carga todos los ToDos desde el archivo."""
        with open(self.todos_file, 'r') as f:
            return json.load(f)
    
    def _save_todos(self, data: Dict) -> None:
        """Persiste los ToDos en el archivo."""
        with open(self.todos_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"ToDos guardados en {self.todos_file}")
    
    def _generate_todo_id(self) -> str:
        """
        Genera un ID único para un ToDo.
        Formato: TODO-YYYYMMDD-XXX
        """
        data = self._load_todos()
        today = datetime.now().strftime('%Y%m%d')
        
        # Contar ToDos del día actual
        count = sum(1 for todo in data['todos'] 
                   if todo['id'].startswith(f'TODO-{today}'))
        
        new_id = f'TODO-{today}-{count + 1:03d}'
        logger.debug(f"ID generado: {new_id}")
        return new_id
    
    def _validate_todo_id(self, todo_id: str) -> bool:
        """
        Valida el formato de un TODO ID.
        Formato esperado: TODO-YYYYMMDD-XXX
        """
        import re
        pattern = r'^TODO-\d{8}-\d{3}$'
        return bool(re.match(pattern, todo_id))
    
    def _validate_affected_files(self, affected_files: List[str]) -> None:
        """
        Valida que affected_files sea una lista válida de paths relativos.
        
        Raises:
            ValueError: Si la validación falla
        """
        if not affected_files:
            raise ValueError("affected_files no puede estar vacío")
        
        if not isinstance(affected_files, list):
            raise ValueError("affected_files debe ser una lista")
        
        for path in affected_files:
            if not isinstance(path, str):
                raise ValueError(f"Path inválido: {path} (debe ser string)")
            
            # Prevenir path traversal
            if '..' in path or path.startswith('/'):
                raise ValueError(f"Path inseguro detectado: {path}")
    
    def _validate_constraints(self, constraints: Dict) -> None:
        """
        Valida que constraints tenga formato DDS v2 compatible.
        
        Raises:
            ValueError: Si la validación falla
        """
        if not isinstance(constraints, dict):
            raise ValueError("constraints debe ser un diccionario")
        
        # max_files_changed es obligatorio
        if 'max_files_changed' not in constraints:
            raise ValueError("constraints debe incluir 'max_files_changed'")
        
        if not isinstance(constraints['max_files_changed'], int):
            raise ValueError("max_files_changed debe ser un entero")
        
        if constraints['max_files_changed'] < 1:
            raise ValueError("max_files_changed debe ser >= 1")
        
        # Validar campos opcionales si existen
        for key in ['no_new_dependencies', 'no_refactor']:
            if key in constraints and not isinstance(constraints[key], bool):
                raise ValueError(f"{key} debe ser booleano")
    
    def create_todo(
        self,
        title: str,
        description: str,
        affected_files: List[str],
        constraints: Dict,
        notes: Optional[str] = None
    ) -> str:
        """
        Crea una nueva tarea.
        
        Args:
            title: Título claro (≤80 caracteres)
            description: Descripción detallada con instrucciones
            affected_files: Lista de paths relativos que serán modificados
            constraints: Constraints DDS v2 (debe incluir max_files_changed)
            notes: Comentarios opcionales del humano
        
        Returns:
            todo_id: ID único de la tarea creada
        
        Raises:
            ValueError: Si las validaciones fallan
        """
        # Validaciones
        if not title or len(title) > 80:
            raise ValueError("title debe tener entre 1 y 80 caracteres")
        
        if not description:
            raise ValueError("description no puede estar vacío")
        
        self._validate_affected_files(affected_files)
        self._validate_constraints(constraints)
        
        # Generar tarea
        todo_id = self._generate_todo_id()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        todo = {
            'id': todo_id,
            'title': title,
            'description': description,
            'affected_files': affected_files,
            'constraints': constraints,
            'status': 'pending',
            'created_at': now,
            'updated_at': now,
            'linked_dds_ids': []
        }
        
        if notes:
            todo['notes'] = notes
        
        # Persistir
        data = self._load_todos()
        data['todos'].append(todo)
        self._save_todos(data)
        
        logger.info(f"ToDo creado: {todo_id} - {title}")
        return todo_id
    
    def get_todo(self, todo_id: str) -> Optional[Dict]:
        """
        Obtiene un ToDo por su ID.
        
        Args:
            todo_id: ID del ToDo
        
        Returns:
            Dict con datos del ToDo o None si no existe
        """
        if not self._validate_todo_id(todo_id):
            logger.warning(f"Formato de ID inválido: {todo_id}")
            return None
        
        data = self._load_todos()
        for todo in data['todos']:
            if todo['id'] == todo_id:
                return todo
        
        logger.warning(f"ToDo no encontrado: {todo_id}")
        return None
    
    def list_todos(self, status: Optional[str] = None) -> List[Dict]:
        """
        Lista todos los ToDos, opcionalmente filtrados por estado.
        
        Args:
            status: Estado para filtrar (None = todos)
        
        Returns:
            Lista de ToDos
        """
        data = self._load_todos()
        todos = data['todos']
        
        if status:
            if status not in self.VALID_STATES:
                logger.warning(f"Estado inválido para filtro: {status}")
                return []
            todos = [t for t in todos if t['status'] == status]
        
        logger.debug(f"Listando {len(todos)} ToDos (status={status})")
        return todos
    
    def update_todo_status(self, todo_id: str, new_status: str) -> bool:
        """
        Actualiza el estado de un ToDo.
        
        Args:
            todo_id: ID del ToDo
            new_status: Nuevo estado (debe ser válido según FSM)
        
        Returns:
            True si se actualizó, False si falló
        
        Raises:
            ValueError: Si la transición de estado no es válida
        """
        # Validaciones
        if not self._validate_todo_id(todo_id):
            raise ValueError(f"Formato de ID inválido: {todo_id}")
        
        if new_status not in self.VALID_STATES:
            raise ValueError(f"Estado inválido: {new_status}")
        
        # Obtener ToDo actual
        data = self._load_todos()
        todo_index = None
        current_todo = None
        
        for i, todo in enumerate(data['todos']):
            if todo['id'] == todo_id:
                todo_index = i
                current_todo = todo
                break
        
        if current_todo is None:
            logger.error(f"ToDo no encontrado: {todo_id}")
            return False
        
        # Validar transición de estado
        current_status = current_todo['status']
        allowed_transitions = self.STATE_TRANSITIONS.get(current_status, set())
        
        if new_status not in allowed_transitions:
            raise ValueError(
                f"Transición de estado inválida: {current_status} → {new_status}. "
                f"Transiciones permitidas desde {current_status}: {allowed_transitions}"
            )
        
        # Actualizar
        data['todos'][todo_index]['status'] = new_status
        data['todos'][todo_index]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._save_todos(data)
        
        logger.info(f"ToDo {todo_id} actualizado: {current_status} → {new_status}")
        return True
    
    def link_dds(self, todo_id: str, dds_id: str) -> bool:
        """
        Vincula un DDS a un ToDo.
        
        Args:
            todo_id: ID del ToDo
            dds_id: ID del DDS generado
        
        Returns:
            True si se vinculó, False si falló
        """
        if not self._validate_todo_id(todo_id):
            logger.error(f"Formato de ID inválido: {todo_id}")
            return False
        
        data = self._load_todos()
        
        for i, todo in enumerate(data['todos']):
            if todo['id'] == todo_id:
                if dds_id not in todo['linked_dds_ids']:
                    data['todos'][i]['linked_dds_ids'].append(dds_id)
                    data['todos'][i]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    self._save_todos(data)
                    logger.info(f"DDS {dds_id} vinculado a ToDo {todo_id}")
                return True
        
        logger.error(f"ToDo no encontrado: {todo_id}")
        return False
