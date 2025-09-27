from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any, Dict

from .config import Settings
from .errors import OdooError, OdooRPCError, OdooValidationError
from .logging import setup_logging
from .odoo_client import OdooClient, OdooClientConfig
from .schemas import (
    CallMethodIn,
    CallMethodOut,
    CreateIn,
    CreateOut,
    ModelFieldsIn,
    ModelFieldsOut,
    ModelsListIn,
    ModelsListOut,
    PingOut,
    ReportDownloadIn,
    ReportDownloadOut,
    SearchReadIn,
    SearchReadOut,
)


logger = logging.getLogger(__name__)

_settings: Settings | None = None
_client: OdooClient | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def get_client() -> OdooClient:
    global _client
    if _client is None:
        s = get_settings()
        cfg = OdooClientConfig(
            base_url=str(s.url),
            db=s.db,
            username=s.username,
            password=s.password,
            timeout=s.timeout,
            verify_ssl=s.verify_ssl,
        )
        _client = OdooClient(cfg)
        uid = _client.authenticate()
        v = _client.version()
        logger.info("odoo.client.init", uid=uid, version=v.get("server_version"))
    return _client


# Handlers
async def handle_ping() -> PingOut:
    req_id = str(uuid.uuid4())
    client = get_client()
    version = client.version()
    logger.info("odoo.ping", request_id=req_id, version=version.get("server_version"))
    return PingOut(server_version=str(version.get("server_version")), uid=client.uid)


async def handle_models_list(payload: Dict[str, Any]) -> ModelsListOut:
    data = ModelsListIn.model_validate(payload)
    req_id = str(uuid.uuid4())
    client = get_client()
    total, items = client.models_list(search=data.search, limit=data.limit, offset=data.offset)
    logger.info("odoo.models.list", request_id=req_id, total=total)
    return ModelsListOut(total=total, items=[{"model": i.get("model"), "name": i.get("name")} for i in items])


async def handle_model_fields(payload: Dict[str, Any]) -> ModelFieldsOut:
    data = ModelFieldsIn.model_validate(payload)
    client = get_client()
    fields = client.fields_get(data.model)
    items = [
        {
            "name": name,
            "ttype": meta.get("type"),
            "required": bool(meta.get("required", False)),
            "readonly": bool(meta.get("readonly", False)),
            "relation": meta.get("relation"),
        }
        for name, meta in fields.items()
    ]
    return ModelFieldsOut(model=data.model, fields=items)  # type: ignore[arg-type]


async def handle_search_read(payload: Dict[str, Any]) -> SearchReadOut:
    data = SearchReadIn.model_validate(payload)
    client = get_client()
    count, records = client.search_read(
        data.model, data.domain, fields=data.fields, limit=data.limit, offset=data.offset, order=data.order
    )
    return SearchReadOut(count=count, records=records)


async def handle_create(payload: Dict[str, Any]) -> CreateOut:
    data = CreateIn.model_validate(payload)
    client = get_client()
    new_id = client.create(data.model, data.values)
    return CreateOut(id=new_id)


async def handle_write(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = CreateIn.model_validate(payload)  # placeholder to avoid duplication
    raise OdooValidationError("Internal schema mismatch; should not be called.")


async def handle_write2(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .schemas import WriteIn, WriteOut

    data = WriteIn.model_validate(payload)
    client = get_client()
    updated = client.write(data.model, data.ids, data.values)
    return WriteOut(updated=updated).model_dump()


async def handle_unlink(payload: Dict[str, Any]) -> Dict[str, Any]:
    from .schemas import UnlinkIn, UnlinkOut

    data = UnlinkIn.model_validate(payload)
    client = get_client()
    deleted = client.unlink(data.model, data.ids)
    return UnlinkOut(deleted=deleted).model_dump()


async def handle_call_method(payload: Dict[str, Any]) -> CallMethodOut:
    data = CallMethodIn.model_validate(payload)
    client = get_client()
    res = client.execute_kw(data.model, data.method, data.args or [], data.kwargs or {})
    return CallMethodOut(result=res)


async def handle_report_download(payload: Dict[str, Any]) -> ReportDownloadOut:
    data = ReportDownloadIn.model_validate(payload)
    client = get_client()
    filename, mimetype, content_b64 = client.report_download(data.report_name, data.ids, data.format or "pdf")
    return ReportDownloadOut(filename=filename, mimetype=mimetype, content_b64=content_b64)


def server_instance():  # type: ignore[no-any-unimported]
    # Lazy import to avoid hard dependency during tests
    from mcp.server import Server  # type: ignore[import-not-found]
    import mcp.types as types  # type: ignore[import-not-found]

    s = Server("odoo")

    # Tools definitions and dispatcher
    from .schemas import WriteIn, WriteOut, UnlinkIn, UnlinkOut

    @s.list_tools()
    async def _list_tools():
        return [
            types.Tool(
                name="odoo.ping",
                description="Vérifie la connexion (auth + version)",
                inputSchema={},
                outputSchema=PingOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.models.list",
                description="Liste des modèles installés",
                inputSchema=ModelsListIn.model_json_schema(),
                outputSchema=ModelsListOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.model.fields",
                description="Liste des champs d’un modèle",
                inputSchema=ModelFieldsIn.model_json_schema(),
                outputSchema=ModelFieldsOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.search_read",
                description="Recherche + lecture",
                inputSchema=SearchReadIn.model_json_schema(),
                outputSchema=SearchReadOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.create",
                description="Création d’un enregistrement",
                inputSchema=CreateIn.model_json_schema(),
                outputSchema=CreateOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.write",
                description="Mise à jour",
                inputSchema=WriteIn.model_json_schema(),
                outputSchema=WriteOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.unlink",
                description="Suppression",
                inputSchema=UnlinkIn.model_json_schema(),
                outputSchema=UnlinkOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.call_method",
                description="Appel arbitraire à execute_kw",
                inputSchema=CallMethodIn.model_json_schema(),
                outputSchema=CallMethodOut.model_json_schema(),
            ),
            types.Tool(
                name="odoo.report.download",
                description="Télécharge un rapport (pdf/xlsx)",
                inputSchema=ReportDownloadIn.model_json_schema(),
                outputSchema=ReportDownloadOut.model_json_schema(),
            ),
        ]

    @s.call_tool(validate_input=True)
    async def _call_tool(name: str, arguments: Dict[str, Any]):
        if name == "odoo.ping":
            return (await handle_ping()).model_dump()
        if name == "odoo.models.list":
            return (await handle_models_list(arguments)).model_dump()
        if name == "odoo.model.fields":
            return (await handle_model_fields(arguments)).model_dump()
        if name == "odoo.search_read":
            return (await handle_search_read(arguments)).model_dump()
        if name == "odoo.create":
            return (await handle_create(arguments)).model_dump()
        if name == "odoo.write":
            return await handle_write2(arguments)
        if name == "odoo.unlink":
            return await handle_unlink(arguments)
        if name == "odoo.call_method":
            return (await handle_call_method(arguments)).model_dump()
        if name == "odoo.report.download":
            return (await handle_report_download(arguments)).model_dump()
        raise OdooRPCError(f"Unknown tool: {name}")

    # Resources
    @s.list_resources()
    async def _list_resources():
        return [
            types.Resource(uri="odoo/version", description="Version serveur + db + uid"),
            types.Resource(uri="odoo/models", description="Liste des modèles (TTL 60s)"),
        ]

    @s.list_resource_templates()
    async def _list_resource_templates():
        return [
            types.ResourceTemplate(uriTemplate="odoo/schema/{model}", description="Schéma détaillé d'un modèle"),
        ]

    @s.read_resource()
    async def _read_resource(uri: str):
        client = get_client()
        if uri == "odoo/version":
            version = client.version()
            payload = {"server_version": version.get("server_version"), "db": get_settings().db, "uid": client.uid}
            return json.dumps(payload)
        if uri == "odoo/models":
            total, items = client.models_list(limit=100, offset=0)
            payload = {"total": total, "items": items}
            return json.dumps(payload)
        if uri.startswith("odoo/schema/"):
            model = uri.split("/", 2)[2]
            fields = client.fields_get(model)
            return json.dumps({"model": model, "fields": fields})
        raise OdooRPCError(f"Unknown resource: {uri}")

    # Prompts
    @s.list_prompts()
    async def _list_prompts():
        return [
            types.Prompt(
                name="make_search_read_prompt",
                description="Décrire un besoin et produire un appel odoo.search_read",
                arguments=[
                    types.PromptArgument(name="model", description="Modèle Odoo concerné"),
                    types.PromptArgument(name="goal_description", description="Objectif métier"),
                ],
            ),
            types.Prompt(
                name="write_values_prompt",
                description="Préparer un dictionnaire values pour create/write (types, relations)",
                arguments=[
                    types.PromptArgument(name="model", description="Modèle Odoo"),
                    types.PromptArgument(name="goal_description", description="Contexte/objectif"),
                ],
            ),
        ]

    @s.get_prompt()
    async def _get_prompt(name: str, args: Dict[str, str] | None):
        args = args or {}
        if name == "make_search_read_prompt":
            messages = [
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=(
                            "Tu aides à formuler un domaine Odoo et un appel odoo.search_read. "
                            "Explique les hypothèses brièvement puis propose l'appel avec domain/fields/order/limit."
                        ),
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=f"Modèle: {args.get('model','')}\nObjectif: {args.get('goal_description','')}",
                    ),
                ),
            ]
            return types.GetPromptResult(messages=messages)
        if name == "write_values_prompt":
            messages = [
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=(
                            "Élabore un dict 'values' cohérent pour {{model}} en respectant les types. "
                            "Explique le traitement des relations M2O/M2M (IDs int, (6,0,[ids]) etc.)."
                        ).replace("{{model}}", args.get("model", "")),
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text", text=f"Contexte: {args.get('goal_description','')}"
                    ),
                ),
            ]
            return types.GetPromptResult(messages=messages)
        raise OdooRPCError(f"Unknown prompt: {name}")

    return s


async def amain() -> None:
    # Lazy import transport to avoid dependency in import path
    from mcp.server.stdio import stdio_server  # type: ignore[import-not-found]

    setup_logging()
    # ensure settings load early for fast fail
    s = get_settings()
    logger.info("mcp.start", settings=s.safe_dict())
    _ = get_client()
    server = server_instance()
    init_options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


def main() -> None:
    try:
        asyncio.run(amain())
    except OdooError as e:
        # Log cleanly and exit
        logging.getLogger(__name__).error("mcp.error", message=str(e))
        raise


if __name__ == "__main__":
    main()
