"""
node_todo

Sistema de gestión de tareas (ToDo) que traduce tareas de alto nivel
en propuestas DDS (Decision-Driven System).

Este componente NO ejecuta código. Solo gestiona tareas y genera propuestas.

Versiones disponibles:
- TodoManager + DDSGenerator: Versión avanzada con FSM y validaciones completas
- TodoRegistry + TodoToDDSConverter: Versión simplificada para uso básico
"""

# Versión avanzada (v2.2)
from .todo_manager import TodoManager
from .dds_generator import DDSGenerator

# Versión simplificada
from .todo_registry import TodoRegistry
from .todo_to_dds import TodoToDDSConverter

__all__ = [
    'TodoManager', 
    'DDSGenerator',
    'TodoRegistry',
    'TodoToDDSConverter'
]
