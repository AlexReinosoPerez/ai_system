"""
TodoRegistry - Gestión CRUD de ToDos en archivo JSON local

Responsabilidad: Persistencia y gestión básica de tareas.
NO incluye lógica de IA ni ejecución automática.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


class TodoRegistry:
    """
    Registro de ToDos con persistencia en archivo JSON.
    
    Gestiona operaciones CRUD sobre tareas (ToDos) almacenadas localmente.
    """
    
    VALID_PRIORITIES = ['low', 'medium', 'high']
    VALID_STATUSES = ['open', 'converted', 'closed']
    
    def __init__(self, json_file: Optional[str] = None):
        """
        Inicializa el registro de ToDos.
        
        Args:
            json_file: Ruta al archivo todo.json. Si es None, usa ubicación por defecto.
        """
        if json_file is None:
            self.json_file = Path(__file__).parent / 'todo.json'
        else:
            self.json_file = Path(json_file)
    
    def _load_todos(self) -> Dict:
        """
        Carga todos los ToDos desde el archivo JSON.
        
        Returns:
            Dict con clave "todos" (lista de diccionarios)
        
        Raises:
            FileNotFoundError: Si el archivo no existe
            json.JSONDecodeError: Si el JSON está corrupto
        """
        if not self.json_file.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {self.json_file}")
        
        try:
            with open(self.json_file, 'r') as f:
                data = json.load(f)
            
            # Validar estructura básica
            if not isinstance(data, dict) or 'todos' not in data:
                raise json.JSONDecodeError(
                    "Estructura JSON inválida: debe contener clave 'todos'",
                    doc=str(self.json_file),
                    pos=0
                )
            
            return data
        
        except json.JSONDecodeError as e:
            # Re-lanzar con mensaje explícito
            raise json.JSONDecodeError(
                f"JSON corrupto en {self.json_file}: {str(e)}",
                doc=e.doc,
                pos=e.pos
            )
    
    def _save_todos(self, data: Dict) -> None:
        """
        Guarda los ToDos en el archivo JSON.
        
        Args:
            data: Diccionario con clave "todos"
        """
        with open(self.json_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_todo(
        self,
        project: str,
        title: str,
        description: str,
        priority: str = "medium"
    ) -> str:
        """
        Crea un nuevo ToDo.
        
        Args:
            project: Nombre del proyecto
            title: Título del ToDo
            description: Descripción detallada
            priority: Prioridad (low|medium|high). Default: medium
        
        Returns:
            ID del ToDo creado (formato: TODO-YYYYMMDD-HHMMSS)
        
        Raises:
            ValueError: Si priority no es válida
        """
        # Validar priority
        if priority not in self.VALID_PRIORITIES:
            raise ValueError(
                f"Prioridad inválida: {priority}. "
                f"Valores válidos: {self.VALID_PRIORITIES}"
            )
        
        # Generar ID único con timestamp
        todo_id = f"TODO-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Crear estructura de ToDo
        todo = {
            "id": todo_id,
            "project": project,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "open",
            "created_at": datetime.now().isoformat()
        }
        
        # Cargar, agregar y guardar
        data = self._load_todos()
        data['todos'].append(todo)
        self._save_todos(data)
        
        return todo_id
    
    def list_todos(self, status: Optional[str] = None) -> List[Dict]:
        """
        Lista todos los ToDos, opcionalmente filtrados por estado.
        
        Args:
            status: Estado para filtrar (open|converted|closed). None = todos
        
        Returns:
            Lista de ToDos
        """
        data = self._load_todos()
        todos = data['todos']
        
        # Filtrar por status si se proporciona
        if status is not None:
            todos = [t for t in todos if t.get('status') == status]
        
        return todos
    
    def get_todo_by_id(self, todo_id: str) -> Optional[Dict]:
        """
        Obtiene un ToDo por su ID.
        
        Args:
            todo_id: ID del ToDo
        
        Returns:
            Dict del ToDo o None si no existe
        """
        data = self._load_todos()
        
        for todo in data['todos']:
            if todo['id'] == todo_id:
                return todo
        
        return None
    
    def update_status(self, todo_id: str, new_status: str) -> bool:
        """
        Actualiza el estado de un ToDo.
        
        Args:
            todo_id: ID del ToDo
            new_status: Nuevo estado (open|converted|closed)
        
        Returns:
            True si se actualizó, False si no se encontró
        
        Raises:
            ValueError: Si new_status no es válido
        """
        # Validar new_status
        if new_status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado inválido: {new_status}. "
                f"Valores válidos: {self.VALID_STATUSES}"
            )
        
        data = self._load_todos()
        
        # Buscar y actualizar
        for todo in data['todos']:
            if todo['id'] == todo_id:
                todo['status'] = new_status
                self._save_todos(data)
                return True
        
        return False
