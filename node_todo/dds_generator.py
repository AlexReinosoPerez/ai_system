"""
DDSGenerator - Traducción determinista de ToDo a DDS v2

Responsabilidad: Generar propuestas DDS draft desde tareas.
NO aprueba ni ejecuta DDS. Solo genera propuestas en estado 'draft'.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from shared.logger import get_logger

logger = get_logger(__name__)


class DDSGenerator:
    """
    Generador de propuestas DDS v2 desde tareas (ToDo).
    
    Traduce campos de ToDo a DDS de forma determinista.
    Los DDS generados siempre tienen status='draft' y requieren aprobación humana.
    """
    
    def __init__(
        self,
        dds_file: Optional[str] = None,
        todos_file: Optional[str] = None
    ):
        """
        Inicializa el generador de DDS.
        
        Args:
            dds_file: Ruta al archivo dds.json. Si es None, usa ubicación por defecto.
            todos_file: Ruta al archivo todos.json. Si es None, usa ubicación por defecto.
        """
        if dds_file is None:
            self.dds_file = Path(__file__).parent.parent / 'node_dds' / 'dds.json'
        else:
            self.dds_file = Path(dds_file)
        
        if todos_file is None:
            self.todos_file = Path(__file__).parent / 'todos.json'
        else:
            self.todos_file = Path(todos_file)
        
        logger.info(f"DDSGenerator inicializado: dds={self.dds_file}, todos={self.todos_file}")
    
    def _load_dds_data(self) -> Dict:
        """Carga el archivo dds.json."""
        if not self.dds_file.exists():
            logger.warning(f"Archivo DDS no existe: {self.dds_file}")
            return {"ddss": []}
        
        with open(self.dds_file, 'r') as f:
            return json.load(f)
    
    def _save_dds_data(self, data: Dict) -> None:
        """Persiste datos en dds.json."""
        with open(self.dds_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.debug(f"DDS guardados en {self.dds_file}")
    
    def _load_todo(self, todo_id: str) -> Optional[Dict]:
        """Carga un ToDo específico."""
        if not self.todos_file.exists():
            logger.error(f"Archivo todos.json no existe: {self.todos_file}")
            return None
        
        with open(self.todos_file, 'r') as f:
            data = json.load(f)
        
        for todo in data.get('todos', []):
            if todo['id'] == todo_id:
                return todo
        
        return None
    
    def _update_todo(self, todo_id: str, updates: Dict) -> None:
        """Actualiza campos de un ToDo."""
        with open(self.todos_file, 'r') as f:
            data = json.load(f)
        
        for i, todo in enumerate(data['todos']):
            if todo['id'] == todo_id:
                data['todos'][i].update(updates)
                data['todos'][i]['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                break
        
        with open(self.todos_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _generate_dds_id(self) -> str:
        """
        Genera un ID único para un DDS.
        Formato: DDS-YYYYMMDD-CODE-XXX
        """
        data = self._load_dds_data()
        today = datetime.now().strftime('%Y%m%d')
        
        # Contar DDS del día actual con tipo CODE
        count = 0
        for dds in data.get('ddss', []):
            if dds['id'].startswith(f'DDS-{today}-CODE'):
                count += 1
        
        new_id = f'DDS-{today}-CODE-{count + 1:03d}'
        logger.debug(f"DDS ID generado: {new_id}")
        return new_id
    
    def _parse_instructions(self, description: str) -> list:
        """
        Convierte description en lista de instrucciones.
        
        Split por líneas que empiezan con números o guiones.
        Si no hay formato estructurado, devuelve descripción completa como única instrucción.
        """
        lines = description.strip().split('\n')
        instructions = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Remover prefijos comunes de listas
            if line.startswith(('- ', '* ', '• ')):
                line = line[2:].strip()
            elif len(line) > 2 and line[0].isdigit() and line[1] in ('.', ')', ':'):
                line = line[2:].strip()
            
            if line:
                instructions.append(line)
        
        # Si no se encontraron instrucciones estructuradas, usar descripción completa
        if not instructions:
            instructions = [description.strip()]
        
        return instructions
    
    def _infer_project_name(self) -> str:
        """
        Infiere el nombre del proyecto desde la estructura del workspace.
        
        Por defecto retorna 'ai_system'. Puede extenderse para leer desde config.
        """
        # TODO: En el futuro, leer desde shared/config.py o .env
        return "ai_system"
    
    def _validate_todo_for_generation(self, todo: Dict) -> None:
        """
        Valida que un ToDo esté listo para generar DDS.
        
        Raises:
            ValueError: Si el ToDo no cumple requisitos
        """
        if todo['status'] != 'pending':
            raise ValueError(
                f"ToDo debe estar en estado 'pending' para generar DDS. "
                f"Estado actual: {todo['status']}"
            )
        
        if not todo['affected_files']:
            raise ValueError("affected_files no puede estar vacío")
        
        if 'max_files_changed' not in todo['constraints']:
            raise ValueError("constraints debe incluir 'max_files_changed'")
    
    def generate_dds_from_todo(self, todo_id: str) -> str:
        """
        Genera un DDS v2 draft desde un ToDo.
        
        Traducción determinista:
        - title → goal
        - description → instructions (parseado)
        - affected_files → allowed_paths
        - constraints → constraints
        - project → inferido
        - tool → 'aider' (hardcoded)
        - version → 2
        - type → 'code_change'
        - status → 'draft' (NUNCA 'approved')
        
        Args:
            todo_id: ID del ToDo fuente
        
        Returns:
            dds_id: ID del DDS generado
        
        Raises:
            ValueError: Si el ToDo no existe o no es válido
        """
        # Cargar ToDo
        todo = self._load_todo(todo_id)
        if todo is None:
            raise ValueError(f"ToDo no encontrado: {todo_id}")
        
        # Validar ToDo
        self._validate_todo_for_generation(todo)
        
        # Generar DDS ID
        dds_id = self._generate_dds_id()
        
        # Traducción determinista
        dds = {
            "id": dds_id,
            "version": 2,
            "type": "code_change",
            "project": self._infer_project_name(),
            "goal": todo['title'],
            "instructions": self._parse_instructions(todo['description']),
            "allowed_paths": todo['affected_files'].copy(),
            "tool": "aider",
            "constraints": todo['constraints'].copy(),
            "status": "draft"  # NUNCA 'approved'
        }
        
        # Agregar metadatos de origen
        dds['metadata'] = {
            "source_todo_id": todo_id,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Persistir DDS
        dds_data = self._load_dds_data()
        if 'ddss' not in dds_data:
            dds_data['ddss'] = []
        dds_data['ddss'].append(dds)
        self._save_dds_data(dds_data)
        
        # Actualizar ToDo: vincular DDS y cambiar estado
        self._update_todo(todo_id, {
            'status': 'draft_generated',
            'linked_dds_ids': todo['linked_dds_ids'] + [dds_id]
        })
        
        logger.info(f"DDS draft generado: {dds_id} desde ToDo {todo_id}")
        return dds_id
