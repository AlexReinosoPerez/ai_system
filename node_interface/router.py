"""
Router - System status reporting for AI System
"""

from shared.logger import setup_logger
from shared.config import config
from node_events.github_reader import GitHubProjectReader
from node_events.summarizer import ProjectSummarizer, SummarizationUnavailable
from node_events.gmail_reader import GmailReader, GmailUnavailable
from node_projects.project_registry import ProjectRegistry, ProjectRegistryError
from node_projects.project_status import ProjectStatus
from node_dds.dds_registry import DDSRegistry, DDSRegistryError
from node_dds.dds_proposal import DDSProposal
from node_programmer.programmer import Programmer, ProgrammerError
from node_programmer.execution_report import ExecutionReport
from node_todo import TodoRegistry, TodoToDDSConverter
from datetime import datetime

logger = setup_logger(__name__)


class Router:
    """Provides system status information"""
    
    def __init__(self):
        """Initialize router"""
        logger.info("Router initialized")
        self._summarizer = None
        self._gmail_reader = None
        self._project_registry = None
        self._project_status = None
        self._dds_registry = None
        self._programmer = None
        self._todo_registry = None
        self._todo_converter = None
    
    def get_system_status(self) -> str:
        """
        Get current system status
        
        Returns:
            Formatted status string
        """
        status = (
            "🧠 AI System Status\n\n"
            "• Interface node: ✅ running\n"
            "• Events node: ⏸️ not started\n"
            "• Programmer node: ⏸️ not started"
        )
        return status
    
    def project(self, name: str) -> str:
        """
        Get project information from GitHub
        
        Args:
            name: Project name
            
        Returns:
            Formatted project status
        """
        logger.info(f"Project query received: {name}")
        
        if name.lower() == "fitnessai":
            reader = GitHubProjectReader("AlexReinosoPerez", "FitnessAi")
            return reader.get_project_status()
        
        return "❌ Proyecto no reconocido"
    
    def project_summary(self, name: str) -> str:
        """
        Get summarized project information from GitHub
        
        Args:
            name: Project name
            
        Returns:
            Summarized project status
        """
        logger.info(f"Project summary query received: {name}")
        
        if name.lower() == "fitnessai":
            if self._summarizer is None:
                self._summarizer = ProjectSummarizer()
            
            reader = GitHubProjectReader("AlexReinosoPerez", "FitnessAi")
            raw_text = reader.get_project_status()
            
            if raw_text.startswith("❌"):
                return raw_text
            
            try:
                return self._summarizer.summarize(raw_text)
            except SummarizationUnavailable as e:
                logger.warning(f"Summarization unavailable: {e}")
                return (
                    "⚠️ Síntesis no disponible en este entorno.\n"
                    "Ejecuta el sistema en tu PC personal con dependencias completas."
                )
        
        return "❌ Proyecto no reconocido"
    
    def inbox(self, count: int = 10) -> str:
        """
        Get recent emails from Gmail inbox
        
        Args:
            count: Number of emails to retrieve
            
        Returns:
            Formatted email list
        """
        logger.info(f"Inbox query received: count={count}")
        
        if self._gmail_reader is None:
            try:
                self._gmail_reader = GmailReader(
                    credentials_path=config.GMAIL_CREDENTIALS_PATH,
                    token_path=config.GMAIL_TOKEN_PATH
                )
            except GmailUnavailable as e:
                logger.warning(f"Gmail initialization failed: {e}")
                return (
                    "⚠️ Gmail no disponible.\n\n"
                    "Posibles causas:\n"
                    "• Falta archivo credentials.json en secrets/\n"
                    "• Librerías de Google no instaladas\n"
                    "• Volumen secrets/ no montado en Docker\n\n"
                    "Consulta DOCKER.md para instrucciones."
                )
        
        try:
            return self._gmail_reader.get_recent_emails(count)
        except GmailUnavailable as e:
            logger.warning(f"Gmail unavailable: {e}")
            return (
                "⚠️ Error accediendo a Gmail.\n\n"
                "Posibles causas:\n"
                "• Token expirado o inválido\n"
                "• Error de autenticación OAuth\n"
                "• Red no disponible\n\n"
                f"Detalle: {str(e)}"
            )
    
    def projects(self) -> str:
        """
        List all registered projects
        
        Returns:
            Formatted project list
        """
        logger.info("Projects list query received")
        
        if self._project_registry is None:
            self._project_registry = ProjectRegistry()
        
        if self._project_status is None:
            self._project_status = ProjectStatus(self._project_registry)
        
        try:
            return self._project_status.summarize_all()
        except ProjectRegistryError as e:
            logger.error(f"Project registry error: {e}")
            return (
                "❌ Error accediendo al registro de proyectos.\n"
                "Verifica que projects.json sea válido."
            )
    
    def project_status(self, name: str) -> str:
        """
        Get status of specific project
        
        Args:
            name: Project name
            
        Returns:
            Formatted project status
        """
        logger.info(f"Project status query received: {name}")
        
        if self._project_registry is None:
            self._project_registry = ProjectRegistry()
        
        if self._project_status is None:
            self._project_status = ProjectStatus(self._project_registry)
        
        try:
            return self._project_status.summarize_one(name)
        except ProjectRegistryError as e:
            logger.error(f"Project registry error: {e}")
            return (
                "❌ Error accediendo al registro de proyectos.\n"
                "Verifica que projects.json sea válido."
            )
    
    def dds_list(self) -> str:
        """
        List all DDS proposals
        
        Returns:
            Formatted proposal list
        """
        logger.info("DDS list query received")
        
        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()
        
        try:
            proposals = self._dds_registry.list_proposals()
            
            if not proposals:
                return "📝 No hay propuestas DDS registradas"
            
            lines = [f"📝 Propuestas DDS ({len(proposals)})\n"]
            
            for proposal in proposals:
                status_icon = "✅" if proposal.status == "approved" else "❌" if proposal.status == "rejected" else "⏳"
                lines.append(f"\n{status_icon} {proposal.id}")
                lines.append(f"   Proyecto: {proposal.project}")
                lines.append(f"   Título: {proposal.title}")
                lines.append(f"   Estado: {proposal.status}")
                lines.append(f"   Creado: {proposal.created_at}")
            
            return "\n".join(lines)
            
        except DDSRegistryError as e:
            logger.error(f"DDS registry error: {e}")
            return (
                "❌ Error accediendo al registro DDS.\n"
                "Verifica que dds.json sea válido."
            )
    
    def dds_new(self, project: str, title: str, description: str) -> str:
        """
        Create new DDS proposal
        
        Args:
            project: Project name
            title: Proposal title
            description: Proposal description
            
        Returns:
            Success message with ID
        """
        logger.info(f"DDS new proposal: {project} - {title}")
        
        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()
        
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            proposal_id = f"DDS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            proposal = DDSProposal(
                id=proposal_id,
                project=project,
                title=title,
                description=description,
                created_at=timestamp,
                status='pending'
            )
            
            self._dds_registry.add_proposal(proposal)
            
            return (
                f"✅ Propuesta creada exitosamente\n\n"
                f"ID: {proposal_id}\n"
                f"Proyecto: {project}\n"
                f"Título: {title}"
            )
            
        except DDSRegistryError as e:
            logger.error(f"DDS registry error: {e}")
            return "❌ Error creando propuesta DDS"
    
    def dds_approve(self, proposal_id: str) -> str:
        """
        Approve DDS proposal
        
        Args:
            proposal_id: Proposal ID to approve
            
        Returns:
            Success or error message
        """
        logger.info(f"DDS approve: {proposal_id}")
        
        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()
        
        try:
            if self._dds_registry.approve(proposal_id):
                return f"✅ Propuesta {proposal_id} aprobada"
            else:
                return f"❌ Propuesta {proposal_id} no encontrada"
                
        except DDSRegistryError as e:
            logger.error(f"DDS registry error: {e}")
            return "❌ Error aprobando propuesta"
    
    def dds_reject(self, proposal_id: str) -> str:
        """
        Reject DDS proposal
        
        Args:
            proposal_id: Proposal ID to reject
            
        Returns:
            Success or error message
        """
        logger.info(f"DDS reject: {proposal_id}")
        
        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()
        
        try:
            if self._dds_registry.reject(proposal_id):
                return f"❌ Propuesta {proposal_id} rechazada"
            else:
                return f"❌ Propuesta {proposal_id} no encontrada"
                
        except DDSRegistryError as e:
            logger.error(f"DDS registry error: {e}")
            return "❌ Error rechazando propuesta"
    
    def execute(self, dds_id: str) -> str:
        """
        Execute DDS proposal
        
        Args:
            dds_id: DDS proposal ID to execute
            
        Returns:
            Execution result message
        """
        logger.info(f"Execution request for DDS: {dds_id}")
        
        if self._programmer is None:
            self._programmer = Programmer()
        
        try:
            # Load DDS to determine action type
            import json
            with open('node_dds/dds.json', 'r') as f:
                data = json.load(f)
            
            dds_found = None
            for proposal in data.get('proposals', []):
                if proposal.get('id') == dds_id:
                    dds_found = proposal
                    break
            
            if not dds_found:
                return f"❌ Error: DDS {dds_id} no encontrado"
            
            action_type = dds_found.get('type', 'noop')
            
            # Dispatch to appropriate execution method
            if action_type == 'code_change':
                report = self._programmer.execute_code_change(dds_id)
            elif action_type == 'touch_file':
                report = self._programmer.execute_touch_file(dds_id)
            elif action_type == 'noop':
                report = self._programmer.execute_noop(dds_id)
            else:
                return f"❌ Error: Tipo de acción no soportado: {action_type}"
            
            return (
                f"✅ DDS {dds_id} ejecutado exitosamente\n\n"
                f"Tipo: {report.action_type}\n"
                f"Estado: {report.status}\n"
                f"Ejecutado: {report.executed_at}\n"
                f"Notas: {report.notes}"
            )
            
        except ProgrammerError as e:
            logger.error(f"Execution error: {e}")
            return f"❌ Error: {str(e)}"
    
    def exec_status(self) -> str:
        """
        Get last execution status
        
        Returns:
            Last execution report or message if no executions
        """
        logger.info("Execution status query received")
        
        if self._programmer is None:
            self._programmer = Programmer()
        
        try:
            report = self._programmer.get_last_report()
            
            if not report:
                return "📊 No hay ejecuciones registradas"
            
            status_icon = "✅" if report.status == "success" else "❌"
            
            return (
                f"📊 Última ejecución\n\n"
                f"{status_icon} DDS: {report.dds_id}\n"
                f"Tipo: {report.action_type}\n"
                f"Estado: {report.status}\n"
                f"Ejecutado: {report.executed_at}\n"
                f"Notas: {report.notes}"
            )
            
        except ProgrammerError as e:
            logger.error(f"Status query error: {e}")
            return "❌ Error consultando estado de ejecuciones"
    
    def todo_list(self) -> str:
        """
        Lista todos los ToDos registrados
        
        Returns:
            Texto formateado con los ToDos
        """
        try:
            if self._todo_registry is None:
                self._todo_registry = TodoRegistry()
            
            todos = self._todo_registry.list_todos()
            
            if not todos:
                return "📝 No hay ToDos registrados"
            
            lines = ["📝 Lista de ToDos\n"]
            for todo in todos:
                priority_icon = "🔴" if todo['priority'] == 'high' else "🟡" if todo['priority'] == 'medium' else "🟢"
                status_icon = "🔓" if todo['status'] == 'open' else "🔄" if todo['status'] == 'converted' else "✅"
                
                lines.append(
                    f"{status_icon} {todo['id']}\n"
                    f"   {priority_icon} {todo['title']}\n"
                    f"   Proyecto: {todo['project']}\n"
                )
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error listing todos: {e}")
            return "❌ Error listando ToDos"
    
    def todo_to_dds(self, todo_id: str) -> str:
        """
        Convierte un ToDo en una propuesta DDS
        
        Args:
            todo_id: ID del ToDo a convertir
        
        Returns:
            Resumen legible de la propuesta DDS generada
        """
        try:
            if self._todo_registry is None:
                self._todo_registry = TodoRegistry()
            if self._todo_converter is None:
                self._todo_converter = TodoToDDSConverter()
            
            todo = self._todo_registry.get_todo(todo_id)
            if not todo:
                return f"❌ ToDo no encontrado: {todo_id}"
            
            dds = self._todo_converter.generate_dds(todo)
            
            return (
                f"🧾 Propuesta DDS Generada\n\n"
                f"📋 DDS ID: {dds['id']}\n"
                f"📦 Proyecto: {dds['project']}\n"
                f"🎯 Objetivo: {dds['goal']}\n"
                f"📝 Instrucciones: {len(dds['instructions'])} pasos\n"
                f"📂 Paths permitidos: {', '.join(dds['allowed_paths'])}\n"
                f"🔧 Herramienta: {dds['tool']}\n"
                f"⚙️ Constraints:\n"
                f"   • Max files: {dds['constraints']['max_files_changed']}\n"
                f"   • No deps: {dds['constraints']['no_new_dependencies']}\n"
                f"   • No refactor: {dds['constraints']['no_refactor']}\n"
                f"📊 Estado: {dds['status']}\n"
                f"🔗 Origen: {dds['source_todo']}\n\n"
                f"⚠️ Nota: Esta es una PROPUESTA. No se ha ejecutado ni guardado."
            )
            
        except ValueError as e:
            logger.error(f"Invalid todo: {e}")
            return f"❌ ToDo inválido: {e}"
        except Exception as e:
            logger.error(f"Error converting todo to dds: {e}")
            return "❌ Error generando propuesta DDS"
    
    def dds_list_proposed(self) -> str:
        """
        Lista DDS con status='proposed'
        
        Returns:
            Texto formateado con DDS propuestos
        """
        try:
            if self._dds_registry is None:
                self._dds_registry = DDSRegistry()
            
            proposed = self._dds_registry.list_proposed()
            
            if not proposed:
                return "🧾 No hay DDS propuestos pendientes de revisión"
            
            lines = ["🧾 DDS Propuestos\n"]
            for dds in proposed:
                lines.append(
                    f"📋 {dds.id}\n"
                    f"   📦 Proyecto: {dds.project}\n"
                    f"   🎯 Título: {dds.title}\n"
                    f"   📊 Estado: {dds.status}\n"
                )
            
            return "\n".join(lines)
            
        except DDSRegistryError as e:
            logger.error(f"Error listing proposed DDS: {e}")
            return "❌ Error listando DDS propuestos"
    
    def dds_approve(self, dds_id: str) -> str:
        """
        Aprueba un DDS propuesto
        
        Args:
            dds_id: ID del DDS a aprobar
        
        Returns:
            Mensaje de confirmación o error
        """
        try:
            if self._dds_registry is None:
                self._dds_registry = DDSRegistry()
            
            success = self._dds_registry.approve(dds_id)
            
            if success:
                return (
                    f"✅ DDS Aprobado\n\n"
                    f"📋 ID: {dds_id}\n"
                    f"📊 Nuevo estado: approved\n\n"
                    f"⚠️ Nota: El DDS ha sido aprobado pero NO se ha ejecutado.\n"
                    f"Usa /execute {dds_id} para ejecutarlo."
                )
            else:
                return f"❌ DDS no encontrado: {dds_id}"
            
        except DDSRegistryError as e:
            logger.error(f"Error approving DDS: {e}")
            return "❌ Error aprobando DDS"
    
    def dds_reject(self, dds_id: str) -> str:
        """
        Rechaza un DDS propuesto
        
        Args:
            dds_id: ID del DDS a rechazar
        
        Returns:
            Mensaje de confirmación o error
        """
        try:
            if self._dds_registry is None:
                self._dds_registry = DDSRegistry()
            
            success = self._dds_registry.reject(dds_id)
            
            if success:
                return (
                    f"❌ DDS Rechazado\n\n"
                    f"📋 ID: {dds_id}\n"
                    f"📊 Nuevo estado: rejected\n\n"
                    f"Este DDS no podrá ser ejecutado."
                )
            else:
                return f"❌ DDS no encontrado: {dds_id}"
            
        except DDSRegistryError as e:
            logger.error(f"Error rejecting DDS: {e}")
            return "❌ Error rechazando DDS"


router = Router()
