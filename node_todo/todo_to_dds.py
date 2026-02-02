"""
TodoToDDSConverter - Conversión de ToDo a propuesta DDS v2

Responsabilidad: Generar propuestas DDS desde ToDos.
NO ejecuta ni aprueba automáticamente.
"""

from datetime import datetime
from typing import Dict


class TodoToDDSConverter:
    """
    Convertidor de ToDo a propuesta DDS v2.
    
    Genera propuestas DDS con status="proposed" que requieren aprobación manual.
    """
    
    def generate_dds(self, todo: Dict) -> Dict:
        """
        Genera una propuesta DDS v2 desde un ToDo.
        
        Args:
            todo: Diccionario con estructura de ToDo
        
        Returns:
            Dict con estructura DDS v2 (status="proposed")
        
        Raises:
            ValueError: Si el ToDo no tiene campos requeridos
        """
        # Validar campos requeridos
        required_fields = ['id', 'project', 'title', 'description']
        missing_fields = [f for f in required_fields if f not in todo]
        
        if missing_fields:
            raise ValueError(
                f"ToDo inválido. Faltan campos requeridos: {missing_fields}"
            )
        
        # Generar estructura DDS v2 exacta según especificación
        dds = {
            "id": f"DDS-GEN-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            "version": 2,
            "type": "code_change",
            "project": todo["project"],
            "goal": f"{todo['title']}: {todo['description']}",
            "instructions": [
                f"Analizar el objetivo: {todo['title']}",
                "Identificar archivos afectados",
                "Implementar cambios mínimos necesarios",
                "Validar que no se rompen tests existentes"
            ],
            "allowed_paths": ["src/", "tests/"],
            "tool": "aider",
            "constraints": {
                "max_files_changed": 5,
                "no_new_dependencies": True,
                "no_refactor": True
            },
            "status": "proposed",
            "source_todo": todo["id"]
        }
        
        # Retornar dict (NO escribir en archivos externos)
        return dds
