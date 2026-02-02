"""
Scheduler - Ejecuta DDS aprobados de forma secuencial

Responsabilidad: Procesar cola de DDS aprobados sin intervención manual.
NO ejecuta en paralelo. Detiene la cola ante el primer error.
"""

from shared.logger import setup_logger
from node_dds.dds_registry import DDSRegistry, DDSRegistryError
from node_programmer.programmer import Programmer, ProgrammerError
from typing import List

logger = setup_logger(__name__)


class Scheduler:
    """
    Scheduler de ejecución secuencial de DDS aprobados.
    
    Ejecuta DDS uno a uno y actualiza sus estados.
    """
    
    def __init__(self):
        """Inicializa el scheduler"""
        self.dds_registry = DDSRegistry()
        self.programmer = Programmer()
        logger.info("Scheduler initialized")
    
    def _get_approved_dds(self) -> List:
        """
        Obtiene DDS con status='approved'
        
        Returns:
            Lista de DDS propuestos ordenados por ID
        """
        try:
            all_proposals = self.dds_registry.list_proposals()
            approved = [p for p in all_proposals if p.status == 'approved']
            
            # Ordenar de forma determinista por ID
            approved.sort(key=lambda p: p.id)
            
            logger.info(f"Found {len(approved)} approved DDS")
            return approved
            
        except DDSRegistryError as e:
            logger.error(f"Error loading approved DDS: {e}")
            return []
    
    def _mark_executed(self, dds_id: str):
        """Marca un DDS como ejecutado exitosamente"""
        try:
            proposals = self.dds_registry.list_proposals()
            for proposal in proposals:
                if proposal.id == dds_id:
                    proposal.status = 'executed'
                    break
            self.dds_registry._save_proposals(proposals)
            logger.info(f"Marked DDS as executed: {dds_id}")
        except Exception as e:
            logger.error(f"Error marking DDS as executed: {e}")
    
    def _mark_failed(self, dds_id: str):
        """Marca un DDS como fallido"""
        try:
            proposals = self.dds_registry.list_proposals()
            for proposal in proposals:
                if proposal.id == dds_id:
                    proposal.status = 'failed'
                    break
            self.dds_registry._save_proposals(proposals)
            logger.info(f"Marked DDS as failed: {dds_id}")
        except Exception as e:
            logger.error(f"Error marking DDS as failed: {e}")
    
    def run(self) -> dict:
        """
        Ejecuta todos los DDS aprobados secuencialmente.
        
        Returns:
            Dict con resumen de ejecución
        """
        logger.info("=== Scheduler execution started ===")
        
        approved_dds = self._get_approved_dds()
        
        if not approved_dds:
            logger.info("No approved DDS to execute")
            return {
                'status': 'completed',
                'executed': 0,
                'failed': 0,
                'message': 'No approved DDS found'
            }
        
        executed_count = 0
        failed_count = 0
        
        for dds in approved_dds:
            logger.info(f"Executing DDS: {dds.id}")
            
            try:
                # Ejecutar usando Programmer
                report = self.programmer.execute_code_change(dds.id)
                
                if report.status == 'success':
                    logger.info(f"DDS executed successfully: {dds.id}")
                    self._mark_executed(dds.id)
                    executed_count += 1
                else:
                    logger.error(f"DDS execution failed: {dds.id} - {report.notes}")
                    self._mark_failed(dds.id)
                    failed_count += 1
                    
                    # Detener scheduler al primer error
                    logger.warning("Scheduler stopped due to execution failure")
                    return {
                        'status': 'stopped_on_error',
                        'executed': executed_count,
                        'failed': failed_count,
                        'failed_dds': dds.id,
                        'message': f'Stopped after failure: {dds.id}'
                    }
                    
            except ProgrammerError as e:
                logger.error(f"Programmer error executing {dds.id}: {e}")
                self._mark_failed(dds.id)
                failed_count += 1
                
                # Detener scheduler al primer error
                logger.warning("Scheduler stopped due to programmer error")
                return {
                    'status': 'stopped_on_error',
                    'executed': executed_count,
                    'failed': failed_count,
                    'failed_dds': dds.id,
                    'message': f'Stopped after error: {str(e)}'
                }
        
        logger.info(f"=== Scheduler execution completed: {executed_count} executed, {failed_count} failed ===")
        
        return {
            'status': 'completed',
            'executed': executed_count,
            'failed': failed_count,
            'message': 'All approved DDS executed successfully'
        }
