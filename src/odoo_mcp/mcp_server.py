from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from .config import Settings
from .errors import OdooError, OdooRPCError
from .logging import setup_logging
from .odoo_client import OdooClient, OdooClientConfig
from .schemas import (
    CallMethodIn,
    CallMethodOut,
    CheckAccessRightsIn,
    CheckAccessRightsOut,
    CopyIn,
    CopyOut,
    CreateIn,
    CreateOut,
    DefaultGetIn,
    DefaultGetOut,
    ExportDataIn,
    ExportDataOut,
    GetMetadataIn,
    GetMetadataOut,
    LoadDataIn,
    LoadDataOut,
    ModelFieldsIn,
    ModelFieldsOut,
    ModelItem,
    ModelsListIn,
    ModelsListOut,
    NameGetIn,
    NameGetOut,
    NameSearchIn,
    NameSearchOut,
    OnchangeIn,
    OnchangeOut,
    PingOut,
    ReadGroupIn,
    ReadGroupOut,
    ReadIn,
    ReadOut,
    ReportDownloadIn,
    ReportDownloadOut,
    SearchCountIn,
    SearchCountOut,
    SearchIn,
    SearchOut,
    SearchReadIn,
    SearchReadOut,
    UnlinkIn,
    UnlinkOut,
    WriteIn,
    WriteOut,
)

logger = logging.getLogger(__name__)

_settings: Settings | None = None
_client: OdooClient | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
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
        logger.info("client.init", extra={"uid": uid, "version": v.get("server_version")})
    return _client


# Handlers
async def handle_ping() -> PingOut:
    req_id = str(uuid.uuid4())
    client = get_client()
    version = client.version()
    logger.info("ping", extra={"request_id": req_id, "version": version.get("server_version")})
    return PingOut(server_version=str(version.get("server_version")), uid=client.uid)


async def handle_models_list(payload: dict[str, Any]) -> ModelsListOut:
    data = ModelsListIn.model_validate(payload)
    req_id = str(uuid.uuid4())
    client = get_client()
    total, items = client.models_list(search=data.search, limit=data.limit, offset=data.offset)
    logger.info("models_list", extra={"request_id": req_id, "total": total})
    formatted_items = [ModelItem(model=str(i.get("model", "")), name=i.get("name")) for i in items]
    return ModelsListOut(total=total, items=formatted_items)


async def handle_model_fields(payload: dict[str, Any]) -> ModelFieldsOut:
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


async def handle_search_read(payload: dict[str, Any]) -> SearchReadOut:
    data = SearchReadIn.model_validate(payload)
    client = get_client()
    count, records = client.search_read(
        data.model,
        data.domain,
        fields=data.fields,
        limit=data.limit,
        offset=data.offset,
        order=data.order,
    )
    return SearchReadOut(count=count, records=records)


async def handle_create(payload: dict[str, Any]) -> CreateOut:
    data = CreateIn.model_validate(payload)
    client = get_client()
    new_id = client.create(data.model, data.values)
    return CreateOut(id=new_id)


async def handle_write(payload: dict[str, Any]) -> dict[str, Any]:
    data = WriteIn.model_validate(payload)
    client = get_client()
    updated = client.write(data.model, data.ids, data.values)
    return WriteOut(updated=updated).model_dump()


async def handle_unlink(payload: dict[str, Any]) -> dict[str, Any]:
    data = UnlinkIn.model_validate(payload)
    client = get_client()
    deleted = client.unlink(data.model, data.ids)
    return UnlinkOut(deleted=deleted).model_dump()


async def handle_call_method(payload: dict[str, Any]) -> CallMethodOut:
    data = CallMethodIn.model_validate(payload)
    client = get_client()
    res = client.execute_kw(data.model, data.method, data.args or [], data.kwargs or {})
    return CallMethodOut(result=res)


async def handle_report_download(payload: dict[str, Any]) -> ReportDownloadOut:
    data = ReportDownloadIn.model_validate(payload)
    client = get_client()
    filename, mimetype, content_b64 = client.report_download(
        data.report_name, data.ids, data.format or "pdf"
    )
    return ReportDownloadOut(filename=filename, mimetype=mimetype, content_b64=content_b64)


async def handle_name_search(payload: dict[str, Any]) -> NameSearchOut:
    data = NameSearchIn.model_validate(payload)
    client = get_client()
    results = client.name_search(data.model, data.name, data.domain, data.limit)
    return NameSearchOut(results=results)


async def handle_name_get(payload: dict[str, Any]) -> NameGetOut:
    data = NameGetIn.model_validate(payload)
    client = get_client()
    results = client.name_get(data.model, data.ids)
    return NameGetOut(results=results)


async def handle_read_group(payload: dict[str, Any]) -> ReadGroupOut:
    data = ReadGroupIn.model_validate(payload)
    client = get_client()
    results = client.read_group(
        data.model, data.domain, data.fields, data.groupby,
        data.offset, data.limit, data.orderby, data.lazy
    )
    return ReadGroupOut(results=results)


async def handle_default_get(payload: dict[str, Any]) -> DefaultGetOut:
    data = DefaultGetIn.model_validate(payload)
    client = get_client()
    defaults = client.default_get(data.model, data.fields)
    return DefaultGetOut(defaults=defaults)


async def handle_onchange(payload: dict[str, Any]) -> OnchangeOut:
    data = OnchangeIn.model_validate(payload)
    client = get_client()
    result = client.onchange(
        data.model, data.ids, data.values, data.field_name, data.field_onchange
    )
    return OnchangeOut(result=result)


async def handle_check_access_rights(payload: dict[str, Any]) -> CheckAccessRightsOut:
    data = CheckAccessRightsIn.model_validate(payload)
    client = get_client()
    has_access = client.check_access_rights(data.model, data.operation, data.raise_exception)
    return CheckAccessRightsOut(has_access=has_access)


async def handle_search_count(payload: dict[str, Any]) -> SearchCountOut:
    data = SearchCountIn.model_validate(payload)
    client = get_client()
    count = client.search_count(data.model, data.domain)
    return SearchCountOut(count=count)


async def handle_copy(payload: dict[str, Any]) -> CopyOut:
    data = CopyIn.model_validate(payload)
    client = get_client()
    new_id = client.copy(data.model, data.record_id, data.default)
    return CopyOut(new_id=new_id)


async def handle_export_data(payload: dict[str, Any]) -> ExportDataOut:
    data = ExportDataIn.model_validate(payload)
    client = get_client()
    result = client.export_data(data.model, data.ids, data.fields, data.raw_data)
    return ExportDataOut(result=result)


async def handle_load_data(payload: dict[str, Any]) -> LoadDataOut:
    data = LoadDataIn.model_validate(payload)
    client = get_client()
    result = client.load(data.model, data.fields, data.data)
    return LoadDataOut(result=result)


async def handle_get_metadata(payload: dict[str, Any]) -> GetMetadataOut:
    data = GetMetadataIn.model_validate(payload)
    client = get_client()
    metadata = client.get_metadata(data.model, data.ids)
    return GetMetadataOut(metadata=metadata)


async def handle_search(payload: dict[str, Any]) -> SearchOut:
    data = SearchIn.model_validate(payload)
    client = get_client()
    ids = client.search(data.model, data.domain, data.offset, data.limit, data.order)
    return SearchOut(ids=ids)


async def handle_read(payload: dict[str, Any]) -> ReadOut:
    data = ReadIn.model_validate(payload)
    client = get_client()
    records = client.read(data.model, data.ids, data.fields)
    return ReadOut(records=records)


def server_instance():  # type: ignore[no-untyped-def]
    # Lazy import to avoid hard dependency during tests
    import mcp.types as types
    from mcp.server import Server

    s = Server("odoo")

    # Helper to ensure inputSchema has type: object at root
    def wrap_schema(schema: dict[str, Any]) -> dict[str, Any]:
        if not schema:
            return {"type": "object", "properties": {}}
        if "type" not in schema:
            schema["type"] = "object"
        return schema

    # Tools definitions and dispatcher
    @s.list_tools()  # type: ignore[no-untyped-call]
    async def _list_tools():  # type: ignore[no-untyped-def]
        return [
            types.Tool(
                name="ping",
                description="Vérifie la connexion (auth + version)",
                inputSchema=wrap_schema({}),
                outputSchema=PingOut.model_json_schema(),
            ),
            types.Tool(
                name="models_list",
                description="Liste des modèles installés",
                inputSchema=wrap_schema(ModelsListIn.model_json_schema()),
                outputSchema=ModelsListOut.model_json_schema(),
            ),
            types.Tool(
                name="model_fields",
                description="Liste des champs d’un modèle",
                inputSchema=wrap_schema(ModelFieldsIn.model_json_schema()),
                outputSchema=ModelFieldsOut.model_json_schema(),
            ),
            types.Tool(
                name="search_read",
                description="Recherche + lecture",
                inputSchema=wrap_schema(SearchReadIn.model_json_schema()),
                outputSchema=SearchReadOut.model_json_schema(),
            ),
            types.Tool(
                name="create",
                description="Création d’un enregistrement",
                inputSchema=wrap_schema(CreateIn.model_json_schema()),
                outputSchema=CreateOut.model_json_schema(),
            ),
            types.Tool(
                name="write",
                description="Mise à jour",
                inputSchema=wrap_schema(WriteIn.model_json_schema()),
                outputSchema=WriteOut.model_json_schema(),
            ),
            types.Tool(
                name="unlink",
                description="Suppression",
                inputSchema=wrap_schema(UnlinkIn.model_json_schema()),
                outputSchema=UnlinkOut.model_json_schema(),
            ),
            types.Tool(
                name="call_method",
                description="Appel arbitraire à execute_kw",
                inputSchema=wrap_schema(CallMethodIn.model_json_schema()),
                outputSchema=CallMethodOut.model_json_schema(),
            ),
            types.Tool(
                name="report_download",
                description="Télécharge un rapport (pdf/xlsx)",
                inputSchema=wrap_schema(ReportDownloadIn.model_json_schema()),
                outputSchema=ReportDownloadOut.model_json_schema(),
            ),
            types.Tool(
                name="search",
                description="Recherche d'IDs uniquement",
                inputSchema=wrap_schema(SearchIn.model_json_schema()),
                outputSchema=SearchOut.model_json_schema(),
            ),
            types.Tool(
                name="read",
                description="Lecture de records par IDs",
                inputSchema=wrap_schema(ReadIn.model_json_schema()),
                outputSchema=ReadOut.model_json_schema(),
            ),
            types.Tool(
                name="name_search",
                description="Recherche par nom (autocomplete-friendly)",
                inputSchema=wrap_schema(NameSearchIn.model_json_schema()),
                outputSchema=NameSearchOut.model_json_schema(),
            ),
            types.Tool(
                name="name_get",
                description="Obtenir les noms affichés des records",
                inputSchema=wrap_schema(NameGetIn.model_json_schema()),
                outputSchema=NameGetOut.model_json_schema(),
            ),
            types.Tool(
                name="read_group",
                description="Agrégation de données (sum, count, avg, etc.)",
                inputSchema=wrap_schema(ReadGroupIn.model_json_schema()),
                outputSchema=ReadGroupOut.model_json_schema(),
            ),
            types.Tool(
                name="default_get",
                description="Obtenir les valeurs par défaut des champs",
                inputSchema=wrap_schema(DefaultGetIn.model_json_schema()),
                outputSchema=DefaultGetOut.model_json_schema(),
            ),
            types.Tool(
                name="onchange",
                description="Simuler le comportement onchange",
                inputSchema=wrap_schema(OnchangeIn.model_json_schema()),
                outputSchema=OnchangeOut.model_json_schema(),
            ),
            types.Tool(
                name="check_access_rights",
                description="Vérifier les droits d'accès utilisateur",
                inputSchema=wrap_schema(CheckAccessRightsIn.model_json_schema()),
                outputSchema=CheckAccessRightsOut.model_json_schema(),
            ),
            types.Tool(
                name="search_count",
                description="Compter les records matchant un domaine",
                inputSchema=wrap_schema(SearchCountIn.model_json_schema()),
                outputSchema=SearchCountOut.model_json_schema(),
            ),
            types.Tool(
                name="copy",
                description="Dupliquer un record",
                inputSchema=wrap_schema(CopyIn.model_json_schema()),
                outputSchema=CopyOut.model_json_schema(),
            ),
            types.Tool(
                name="export_data",
                description="Exporter des données",
                inputSchema=wrap_schema(ExportDataIn.model_json_schema()),
                outputSchema=ExportDataOut.model_json_schema(),
            ),
            types.Tool(
                name="load",
                description="Importer/charger des données en masse",
                inputSchema=wrap_schema(LoadDataIn.model_json_schema()),
                outputSchema=LoadDataOut.model_json_schema(),
            ),
            types.Tool(
                name="get_metadata",
                description="Obtenir les métadonnées (create/write info)",
                inputSchema=wrap_schema(GetMetadataIn.model_json_schema()),
                outputSchema=GetMetadataOut.model_json_schema(),
            ),
        ]

    @s.call_tool(validate_input=True)  # type: ignore[misc]
    async def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "ping":
            return (await handle_ping()).model_dump()
        if name == "models_list":
            return (await handle_models_list(arguments)).model_dump()
        if name == "model_fields":
            return (await handle_model_fields(arguments)).model_dump()
        if name == "search_read":
            return (await handle_search_read(arguments)).model_dump()
        if name == "create":
            return (await handle_create(arguments)).model_dump()
        if name == "write":
            return await handle_write(arguments)
        if name == "unlink":
            return await handle_unlink(arguments)
        if name == "call_method":
            return (await handle_call_method(arguments)).model_dump()
        if name == "report_download":
            return (await handle_report_download(arguments)).model_dump()
        if name == "search":
            return (await handle_search(arguments)).model_dump()
        if name == "read":
            return (await handle_read(arguments)).model_dump()
        if name == "name_search":
            return (await handle_name_search(arguments)).model_dump()
        if name == "name_get":
            return (await handle_name_get(arguments)).model_dump()
        if name == "read_group":
            return (await handle_read_group(arguments)).model_dump()
        if name == "default_get":
            return (await handle_default_get(arguments)).model_dump()
        if name == "onchange":
            return (await handle_onchange(arguments)).model_dump()
        if name == "check_access_rights":
            return (await handle_check_access_rights(arguments)).model_dump()
        if name == "search_count":
            return (await handle_search_count(arguments)).model_dump()
        if name == "copy":
            return (await handle_copy(arguments)).model_dump()
        if name == "export_data":
            return (await handle_export_data(arguments)).model_dump()
        if name == "load":
            return (await handle_load_data(arguments)).model_dump()
        if name == "get_metadata":
            return (await handle_get_metadata(arguments)).model_dump()
        raise OdooRPCError(f"Unknown tool: {name}")

    # Resources
    @s.list_resources()  # type: ignore[no-untyped-call]
    async def _list_resources():  # type: ignore[no-untyped-def]
        return [
            types.Resource(uri="odoo://version", name="Odoo Version", description="Version serveur + db + uid"),  # type: ignore[call-arg]
            types.Resource(uri="odoo://models", name="Odoo Models", description="Liste des modèles (TTL 60s)"),  # type: ignore[call-arg]
        ]

    @s.list_resource_templates()  # type: ignore[no-untyped-call]
    async def _list_resource_templates():  # type: ignore[no-untyped-def]
        return [
            types.ResourceTemplate(  # type: ignore[call-arg]
                uriTemplate="odoo://schema/{model}", name="Odoo Model Schema", description="Schéma détaillé d'un modèle"
            ),
        ]

    @s.read_resource()  # type: ignore[no-untyped-call, misc]
    async def _read_resource(uri: str) -> str:
        client = get_client()
        if uri == "odoo://version":
            version = client.version()
            payload = {
                "server_version": version.get("server_version"),
                "db": get_settings().db,
                "uid": client.uid,
            }
            return json.dumps(payload)
        if uri == "odoo://models":
            total, items = client.models_list(limit=100, offset=0)
            payload = {"total": total, "items": items}
            return json.dumps(payload)
        if uri.startswith("odoo://schema/"):
            model = uri.split("/", 2)[2]
            fields = client.fields_get(model)
            return json.dumps({"model": model, "fields": fields})
        raise OdooRPCError(f"Unknown resource: {uri}")

    # Prompts
    @s.list_prompts()  # type: ignore[no-untyped-call]
    async def _list_prompts():  # type: ignore[no-untyped-def]
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

    @s.get_prompt()  # type: ignore[no-untyped-call, misc]
    async def _get_prompt(name: str, args: dict[str, str] | None):  # type: ignore[no-untyped-def]
        args = args or {}
        if name == "make_search_read_prompt":
            messages = [
                types.PromptMessage(
                    role="assistant",
                    content=types.TextContent(
                        type="text",
                        text=(
                            "Tu aides à formuler un domaine Odoo et un appel odoo.search_read. "
                            "Explique les hypothèses brièvement puis propose l'appel avec "
                            "domain/fields/order/limit."
                        ),
                    ),
                ),
                types.PromptMessage(
                    role="user",
                    content=types.TextContent(
                        type="text",
                        text=(
                            f"Modèle: {args.get('model','')}\n"
                            f"Objectif: {args.get('goal_description','')}"
                        ),
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
                            "Élabore un dict 'values' cohérent pour {{model}} en "
                            "respectant les types. "
                            "Explique le traitement des relations M2O/M2M "
                            "(IDs int, (6,0,[ids]) etc.)."
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
    from mcp.server.stdio import stdio_server

    setup_logging()
    # ensure settings load early for fast fail
    s = get_settings()
    logger.info("mcp.start", extra={"settings": s.safe_dict()})
    _ = get_client()
    server = server_instance()  # type: ignore[no-untyped-call]
    init_options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init_options)


def main() -> None:
    try:
        asyncio.run(amain())
    except OdooError as e:
        # Log cleanly and exit
        logging.getLogger(__name__).error("mcp.error: %s", str(e))
        raise


if __name__ == "__main__":
    main()
