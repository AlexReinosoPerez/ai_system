"""
node_todo

Sistema de gestión de tareas (ToDo) que traduce tareas de alto nivel
en propuestas DDS v2 para ejecución gobernada.

Este componente NO ejecuta código. Solo gestiona tareas y genera propuestas.
"""

from .todo_manager import TodoManager
from .dds_generator import DDSGenerator

__all__ = ['TodoManager', 'DDSGenerator']
