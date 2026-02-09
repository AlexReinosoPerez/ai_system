"""
Router - Governed dispatch layer for AI System

The Router is the ONLY entry point for any interface to interact with the system.
All actions must pass through dispatch() with a valid ContractRequest.

Internal methods (prefixed with _) contain the existing logic and are NOT
accessible to interfaces directly.
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
from node_interface.contract import (
    Action,
    ContractRequest,
    ContractResponse,
    ContractError,
    is_read_only,
    is_write,
    validate_payload,
    validate_source_permission,
)
from datetime import datetime
import json
import os
import time

logger = setup_logger(__name__)

# ──────────────────────────────────────────────
# AUDIT PERSISTENCE
# ──────────────────────────────────────────────

AUDIT_FILE = "audits/contract_audit.jsonl"


# Fields extracted from payload for traceability (not the full payload)
_TRACEABLE_KEYS = {"dds_id", "proposal_id", "todo_id", "name", "project"}


def _extract_payload_summary(payload: dict) -> dict:
    """Extract only traceable identifiers from payload — never secrets or blobs."""
    return {k: v for k, v in payload.items() if k in _TRACEABLE_KEYS}


def _persist_audit(
    request: ContractRequest,
    response: ContractResponse,
    *,
    level: str = "info",
    error_detail: str = "",
    duration_ms: int = 0,
) -> None:
    """
    Append audit entry to JSONL file (one JSON object per line, append-only).
    
    Enriched fields (v1.1):
        level: info | decision | guard_reject | error
        payload_summary: traceable identifiers (dds_id, proposal_id, etc.)
        error_detail: why the request failed (empty on success)
        duration_ms: wall-clock time of the full dispatch
    
    Never raises — audit failure must not break dispatch.
    """
    try:
        entry = {
            "audit_id": response.audit_id,
            "timestamp": request.timestamp,
            "source": request.source,
            "user_id": request.user_id,
            "action": request.action.value if isinstance(request.action, Action) else str(request.action),
            "level": level,
            "payload_keys": list(request.payload.keys()),
            "payload_summary": _extract_payload_summary(request.payload),
            "status": response.status,
            "read_only": response.read_only,
            "duration_ms": duration_ms,
        }
        if error_detail:
            entry["error_detail"] = error_detail
        os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Audit persistence failed (non-fatal): {e}")


# ──────────────────────────────────────────────
# USER AUTHENTICATION
# ──────────────────────────────────────────────

def _is_user_allowed(user_id: str) -> bool:
    """
    Check if user_id is in the allowed list.
    
    If ALLOWED_USER_IDS is empty, auth is DISABLED (development mode).
    This is intentional: the system should work without auth configured,
    but become strict the moment you set the env var.
    """
    allowed_raw = config.ALLOWED_USER_IDS
    if not allowed_raw or not allowed_raw.strip():
        return True  # Auth disabled — development mode
    
    allowed_ids = {uid.strip() for uid in allowed_raw.split(",") if uid.strip()}
    return str(user_id) in allowed_ids


class Router:
    """
    Governed Router — single dispatch entry point for all interfaces.

    Public API: dispatch(request) only.
    All business methods are private (_prefixed) and unreachable from interfaces.
    """

    def __init__(self):
        """Initialize router and internal dispatch table"""
        logger.info("Router initialized")
        self._summarizer = None
        self._gmail_reader = None
        self._project_registry = None
        self._project_status = None
        self._dds_registry = None
        self._programmer = None
        self._todo_registry = None
        self._todo_converter = None

        # Dispatch table: Action -> handler method
        # This is the ONLY mapping between contract actions and internal logic.
        self._dispatch_table = {
            Action.SYSTEM_STATUS: self._handle_system_status,
            Action.PROJECT_INFO: self._handle_project_info,
            Action.PROJECT_SUMMARY: self._handle_project_summary,
            Action.PROJECT_LIST: self._handle_project_list,
            Action.PROJECT_STATUS: self._handle_project_status,
            Action.INBOX: self._handle_inbox,
            Action.DDS_LIST: self._handle_dds_list,
            Action.DDS_LIST_PROPOSED: self._handle_dds_list_proposed,
            Action.EXEC_STATUS: self._handle_exec_status,
            Action.TODO_LIST: self._handle_todo_list,
            Action.DDS_NEW: self._handle_dds_new,
            Action.DDS_APPROVE: self._handle_dds_approve,
            Action.DDS_REJECT: self._handle_dds_reject,
            Action.EXECUTE: self._handle_execute,
            Action.TODO_TO_DDS: self._handle_todo_to_dds,
        }

    # ──────────────────────────────────────────────
    # PUBLIC API — the ONLY method interfaces may call
    # ──────────────────────────────────────────────

    def dispatch(self, request: ContractRequest) -> ContractResponse:
        """
        Single entry point for all interface actions.

        Guards (in order):
        1. Action type validation
        2. User authentication (if ALLOWED_USER_IDS is set)
        3. Source permission check
        4. Payload schema validation
        5. Handler execution

        Every request/response pair is persisted to the audit log.

        Args:
            request: A valid ContractRequest

        Returns:
            ContractResponse with status, message, and optional data
        """
        _t0 = time.monotonic()

        logger.info(
            f"Contract dispatch: action={request.action.value} "
            f"source={request.source} user={request.user_id}"
        )

        # Helper: compute elapsed ms since dispatch start
        def _elapsed_ms() -> int:
            return int((time.monotonic() - _t0) * 1000)

        # 1. Validate action is in whitelist
        if not isinstance(request.action, Action):
            logger.error(f"Invalid action type: {type(request.action)}")
            response = ContractResponse(
                status="error",
                message="❌ Acción no válida",
                action=None,
                read_only=True,
            )
            _persist_audit(request, response,
                           level="guard_reject",
                           error_detail="action_not_in_whitelist",
                           duration_ms=_elapsed_ms())
            return response

        # 2. User authentication
        if not _is_user_allowed(request.user_id):
            logger.warning(
                f"Unauthorized user: {request.user_id} "
                f"attempted {request.action.value}"
            )
            response = ContractResponse(
                status="error",
                message="❌ Usuario no autorizado",
                action=request.action,
                read_only=is_read_only(request.action),
            )
            _persist_audit(request, response,
                           level="guard_reject",
                           error_detail=f"user_not_allowed:{request.user_id}",
                           duration_ms=_elapsed_ms())
            return response

        # 3. Source permission check
        try:
            validate_source_permission(request.source, request.action)
        except ContractError as e:
            logger.warning(f"Source permission denied: {e}")
            response = ContractResponse(
                status="error",
                message=f"❌ Permiso denegado: {str(e)}",
                action=request.action,
                read_only=is_read_only(request.action),
            )
            _persist_audit(request, response,
                           level="guard_reject",
                           error_detail=f"source_denied:{request.source}",
                           duration_ms=_elapsed_ms())
            return response

        # 4. Validate payload against schema
        try:
            validate_payload(request.action, request.payload)
        except ContractError as e:
            logger.warning(f"Payload validation failed: {e}")
            response = ContractResponse(
                status="error",
                message=f"❌ Payload inválido: {str(e)}",
                action=request.action,
                read_only=is_read_only(request.action),
            )
            _persist_audit(request, response,
                           level="guard_reject",
                           error_detail=f"payload_invalid:{str(e)}",
                           duration_ms=_elapsed_ms())
            return response

        # 5. Lookup handler
        handler = self._dispatch_table.get(request.action)
        if handler is None:
            logger.error(f"No handler for action: {request.action.value}")
            response = ContractResponse(
                status="error",
                message=f"❌ Acción sin handler: {request.action.value}",
                action=request.action,
                read_only=is_read_only(request.action),
            )
            _persist_audit(request, response,
                           level="error",
                           error_detail="no_handler_registered",
                           duration_ms=_elapsed_ms())
            return response

        # 6. Execute handler
        error_detail = ""
        try:
            message = handler(request.payload)
            response = ContractResponse(
                status="ok",
                message=message,
                action=request.action,
                read_only=is_read_only(request.action),
            )
        except Exception as e:
            logger.error(f"Handler error for {request.action.value}: {e}")
            error_detail = f"handler_exception:{type(e).__name__}:{str(e)[:200]}"
            response = ContractResponse(
                status="error",
                message=f"❌ Error interno: {str(e)}",
                action=request.action,
                read_only=is_read_only(request.action),
            )

        # 7. Persist audit (always, regardless of success/failure)
        level = "info"
        if is_write(request.action) and response.status == "ok":
            level = "decision"
        elif response.status == "error":
            level = "error"
        _persist_audit(request, response,
                       level=level,
                       error_detail=error_detail,
                       duration_ms=_elapsed_ms())
        return response

    # ──────────────────────────────────────────────
    # PRIVATE HANDLERS — not accessible from interfaces
    # Each handler receives payload dict and returns a string message.
    # The existing logic is preserved exactly as-is.
    # ──────────────────────────────────────────────

    def _handle_system_status(self, payload: dict) -> str:
        status = (
            "🧠 AI System Status\n\n"
            "• Interface node: ✅ running\n"
            "• Events node: ⏸️ not started\n"
            "• Programmer node: ⏸️ not started"
        )
        return status

    def _handle_project_info(self, payload: dict) -> str:
        name = payload["name"]
        logger.info(f"Project query received: {name}")

        if name.lower() == "fitnessai":
            reader = GitHubProjectReader("AlexReinosoPerez", "FitnessAi")
            return reader.get_project_status()

        return "❌ Proyecto no reconocido"

    def _handle_project_summary(self, payload: dict) -> str:
        name = payload["name"]
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

    def _handle_inbox(self, payload: dict) -> str:
        count = payload.get("count", 10)
        logger.info(f"Inbox query received: count={count}")

        if self._gmail_reader is None:
            try:
                self._gmail_reader = GmailReader(
                    credentials_path=config.GMAIL_CREDENTIALS_PATH,
                    token_path=config.GMAIL_TOKEN_PATH,
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

    def _handle_project_list(self, payload: dict) -> str:
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

    def _handle_project_status(self, payload: dict) -> str:
        name = payload["name"]
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

    def _handle_dds_list(self, payload: dict) -> str:
        logger.info("DDS list query received")

        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()

        try:
            proposals = self._dds_registry.list_proposals()

            if not proposals:
                return "📝 No hay propuestas DDS registradas"

            lines = [f"📝 Propuestas DDS ({len(proposals)})\n"]

            for proposal in proposals:
                status_icon = {
                    "approved": "✅",
                    "rejected": "❌",
                    "proposed": "📋",
                    "executed": "🏁",
                    "failed": "💥",
                }.get(proposal.status, "⏳")
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

    def _handle_dds_new(self, payload: dict) -> str:
        project = payload["project"]
        title = payload["title"]
        description = payload["description"]
        logger.info(f"DDS new proposal: {project} - {title}")

        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()

        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            proposal_id = f"DDS-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

            proposal = DDSProposal(
                id=proposal_id,
                project=project,
                title=title,
                description=description,
                created_at=timestamp,
                status="proposed",
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

    def _handle_dds_approve(self, payload: dict) -> str:
        proposal_id = payload["proposal_id"]
        logger.info(f"DDS approve: {proposal_id}")

        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()

        try:
            success = self._dds_registry.approve(proposal_id)

            if success:
                return (
                    f"✅ DDS Aprobado\n\n"
                    f"📋 ID: {proposal_id}\n"
                    f"📊 Nuevo estado: approved\n\n"
                    f"⚠️ Nota: El DDS ha sido aprobado pero NO se ha ejecutado.\n"
                    f"Usa /execute {proposal_id} para ejecutarlo."
                )
            else:
                return f"❌ DDS no encontrado: {proposal_id}"

        except DDSRegistryError as e:
            logger.error(f"DDS registry error: {e}")
            return "❌ Error aprobando DDS"

    def _handle_dds_reject(self, payload: dict) -> str:
        proposal_id = payload["proposal_id"]
        logger.info(f"DDS reject: {proposal_id}")

        if self._dds_registry is None:
            self._dds_registry = DDSRegistry()

        try:
            success = self._dds_registry.reject(proposal_id)

            if success:
                return (
                    f"❌ DDS Rechazado\n\n"
                    f"📋 ID: {proposal_id}\n"
                    f"📊 Nuevo estado: rejected\n\n"
                    f"Este DDS no podrá ser ejecutado."
                )
            else:
                return f"❌ DDS no encontrado: {proposal_id}"

        except DDSRegistryError as e:
            logger.error(f"DDS registry error: {e}")
            return "❌ Error rechazando DDS"

    def _handle_execute(self, payload: dict) -> str:
        dds_id = payload["dds_id"]
        logger.info(f"Execution request for DDS: {dds_id}")

        if self._programmer is None:
            self._programmer = Programmer()

        try:
            with open("node_dds/dds.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise ProgrammerError(
                "[dds_error] No se encontró el archivo dds.json. "
                "Verifica que node_dds/dds.json existe y es válido."
            )
        except json.JSONDecodeError:
            raise ProgrammerError(
                "[dds_error] dds.json corrupto. "
                "El archivo no contiene JSON válido."
            )

        dds_found = None
        for proposal in data.get("proposals", []):
            if proposal.get("id") == dds_id:
                dds_found = proposal
                break

        if not dds_found:
            raise ProgrammerError(
                f"[dds_error] DDS {dds_id} not found in registry. "
                f"Usa /dds para ver los DDS disponibles."
            )

        if dds_found.get("status") != "approved":
            raise ProgrammerError(
                f"[dds_error] DDS {dds_id} not found or not approved. "
                f"Estado actual: {dds_found.get('status')}. "
                f"Aprueba primero con /dds_approve {dds_id}"
            )

        action_type = dds_found.get("type", "noop")

        try:
            if action_type in ("code_change", "code_fix"):
                report = self._programmer.execute_code_change(dds_id)
            elif action_type == "touch_file":
                report = self._programmer.execute_touch_file(dds_id)
            elif action_type == "noop":
                report = self._programmer.execute_noop(dds_id)
            else:
                raise ProgrammerError(
                    f"[dds_error] Tipo de acción no soportado: '{action_type}'. "
                    f"Solo code_change, code_fix, touch_file y noop son válidos."
                )

            return (
                f"✅ DDS {dds_id} ejecutado exitosamente\n\n"
                f"Tipo: {report.action_type}\n"
                f"Estado: {report.status}\n"
                f"Ejecutado: {report.executed_at}\n"
                f"Notas: {report.notes}"
            )

        except ProgrammerError as e:
            error_msg = str(e)
            # Classify the error for human triage
            if "already been executed" in error_msg or "already executed" in error_msg:
                category = "dds_error"
                hint = "Este DDS ya fue ejecutado. No se puede re-ejecutar."
            elif "not found or not approved" in error_msg:
                category = "dds_error"
                hint = "Verifica que el DDS existe y está aprobado con /dds"
            elif "not found in registry" in error_msg:
                category = "dds_error"
                hint = "No existe un DDS con ese ID. Usa /dds para ver los disponibles."
            elif "Missing" in error_msg or "missing" in error_msg or "Invalid" in error_msg:
                category = "dds_error"
                hint = "El DDS tiene campos incompletos o inválidos. Revisa su estructura."
            elif "not found" in error_msg.lower() and ("command" in error_msg.lower() or "aider" in error_msg.lower()):
                category = "env_error"
                hint = "Aider no está instalado. Ejecuta: pip install aider-chat"
            elif "Timeout" in error_msg or "timeout" in error_msg:
                category = "exec_error"
                hint = "La ejecución excedió el tiempo límite. Revisa la complejidad del DDS."
            elif "Constraint" in error_msg or "constraint" in error_msg:
                category = "exec_error"
                hint = "La ejecución violó restricciones del DDS (max files, etc.)."
            else:
                category = "exec_error"
                hint = "Error durante la ejecución. Revisa los logs y reports.json."

            logger.error(f"Execution error [{category}]: {error_msg}")
            # Re-raise with category prefix so dispatch() captures it
            # in error_detail and marks status=error in the audit
            raise ProgrammerError(
                f"[{category}] {error_msg[:200]}\n"
                f"Acción: {hint}"
            ) from e

    def _handle_exec_status(self, payload: dict) -> str:
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

    def _handle_todo_list(self, payload: dict) -> str:
        try:
            if self._todo_registry is None:
                self._todo_registry = TodoRegistry()

            todos = self._todo_registry.list_todos()

            if not todos:
                return "📝 No hay ToDos registrados"

            lines = ["📝 Lista de ToDos\n"]
            for todo in todos:
                priority_icon = (
                    "🔴" if todo["priority"] == "high"
                    else "🟡" if todo["priority"] == "medium"
                    else "🟢"
                )
                status_icon = (
                    "🔓" if todo["status"] == "open"
                    else "🔄" if todo["status"] == "converted"
                    else "✅"
                )

                lines.append(
                    f"{status_icon} {todo['id']}\n"
                    f"   {priority_icon} {todo['title']}\n"
                    f"   Proyecto: {todo['project']}\n"
                )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Error listing todos: {e}")
            return "❌ Error listando ToDos"

    def _handle_todo_to_dds(self, payload: dict) -> str:
        todo_id = payload["todo_id"]
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

    def _handle_dds_list_proposed(self, payload: dict) -> str:
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


# Global router instance
router = Router()
