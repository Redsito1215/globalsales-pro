# -*- coding: utf-8 -*-
"""Asistente IA para recomendar y generar informes sobre el catálogo existente."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from config.settings import settings
from paquetes.reportes import compuestos, services

SCOPE_SIMPLE = "simple"
SCOPE_COMPOUND = "compuesto"
SCOPE_ALL = "all"
VALID_SCOPES = frozenset({SCOPE_SIMPLE, SCOPE_COMPOUND, SCOPE_ALL})


class AIServiceError(RuntimeError):
    """Error controlado de configuración o comunicación con el proveedor de IA."""

    def __init__(self, code: str, message: str, *, http_status: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status

SCOPE_META: dict[str, dict[str, str]] = {
    SCOPE_SIMPLE: {
        "label": "Informes operativos",
        "subtitle": "Seguimiento táctico de la operación diaria (pedidos, stock, soporte, proveedores).",
        "prefix": "RS",
        "data_layer": "operativo",
    },
    SCOPE_COMPOUND: {
        "label": "Informes estratégicos",
        "subtitle": "Análisis estratégico desde ClickHouse (ventas, márgenes, tendencias y rankings).",
        "prefix": "RC",
        "data_layer": "estrategico",
    },
}

_SIMPLE_DEFAULTS = ["RS-01", "RS-02", "RS-03", "RS-04", "RS-07"]
_COMPOUND_DEFAULTS = ["RC-01", "RC-02", "RC-04", "RC-07", "RC-08"]


def normalize_scope(scope: str | None) -> str:
    value = (scope or SCOPE_ALL).strip().lower()
    if value in ("compuestos", "compuesto", "rc", "complex"):
        return SCOPE_COMPOUND
    if value in ("simples", "simple", "rs", "operativo"):
        return SCOPE_SIMPLE
    if value in VALID_SCOPES:
        return value
    return SCOPE_ALL


def _matches_scope(rep: dict[str, Any], scope: str) -> bool:
    if scope == SCOPE_ALL:
        return True
    return rep.get("tipo") == scope


def _catalog_entries(*, scope: str = SCOPE_ALL) -> list[dict[str, Any]]:
    scope = normalize_scope(scope)
    rows: list[dict[str, Any]] = []
    for rep in services.list_catalog():
        row = {**rep, "tipo": SCOPE_SIMPLE, "tipo_label": "Simple", "data_layer": "operativo"}
        if _matches_scope(row, scope):
            rows.append(row)
    for rep in compuestos.list_complex_catalog():
        row = {
            **rep,
            "tipo": SCOPE_COMPOUND,
            "tipo_label": "Compuesto",
            "data_layer": rep.get("data_layer") or "estrategico",
        }
        if _matches_scope(row, scope):
            rows.append(row)
    return rows


def list_ai_catalog(*, scope: str = SCOPE_ALL) -> dict[str, Any]:
    scope = normalize_scope(scope)
    simples = _catalog_entries(scope=SCOPE_SIMPLE)
    compuestos_rows = _catalog_entries(scope=SCOPE_COMPOUND)
    scoped = _catalog_entries(scope=scope)
    return {
        "scope": scope,
        "counts": {
            "simples": len(simples),
            "compuestos": len(compuestos_rows),
            "total": len(simples) + len(compuestos_rows),
            "scoped": len(scoped),
        },
        "scope_meta": SCOPE_META.get(scope) if scope != SCOPE_ALL else None,
        "reports": [
            {
                "id": r["id"],
                "name": r.get("name", ""),
                "tipo": r.get("tipo"),
                "tipo_label": r.get("tipo_label"),
                "para_que": r.get("para_que", ""),
                "quien": r.get("quien", ""),
                "data_layer": r.get("data_layer"),
                "columns": r.get("columns") or [],
            }
            for r in scoped
        ],
    }


def _catalog_for_llm(*, scope: str = SCOPE_ALL) -> list[dict[str, str]]:
    return [
        {
            "id": r["id"],
            "tipo": r.get("tipo", SCOPE_SIMPLE),
            "tipo_label": r.get("tipo_label", ""),
            "data_layer": r.get("data_layer", ""),
            "name": r.get("name", ""),
            "para_que": r.get("para_que", ""),
            "quien": r.get("quien", ""),
        }
        for r in _catalog_entries(scope=scope)
    ]


def _tokenize(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-záéíóúñü0-9]+", (text or "").lower()) if len(w) > 2}


# Sinónimos y frases frecuentes (español) para el motor local sin OpenAI.
_QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "stock": ("inventario", "existencias", "reposicion", "reponer", "minimo"),
    "pago": ("cobro", "cobrar", "pagos", "credito", "deuda"),
    "pendiente": ("pendientes", "revision", "aprobar", "aprobacion", "espera"),
    "venta": ("ventas", "ingresos", "facturacion", "comercial"),
    "margen": ("utilidad", "ganancia", "rentabilidad"),
    "proveedor": ("proveedores", "vendor", "abastecimiento"),
    "envio": ("envios", "enviado", "logistica", "tracking", "despacho"),
    "chat": ("mensaje", "mensajes", "soporte", "atencion", "cliente"),
    "cupon": ("cupones", "descuento", "promocion"),
    "ranking": ("top", "lider", "rezagado", "peor", "mejor"),
    "rotacion": ("rotar", "giro", "inventario"),
    "datos": ("elt", "modelo", "carga", "fact_ventas", "dw"),
}

# (frases clave, report_id) — prioridad alta en motor local
_INTENT_PHRASES: tuple[tuple[str, str], ...] = (
    ("stock bajo", "RS-03"),
    ("poco stock", "RS-03"),
    ("existencias bajas", "RS-03"),
    ("reponer inventario", "RS-03"),
    ("pago pendiente", "RS-02"),
    ("sin pagar", "RS-02"),
    ("a credito", "RS-02"),
    ("solicitud pendiente", "RS-01"),
    ("pendiente de revision", "RS-01"),
    ("sin aprobar", "RS-01"),
    ("chat sin responder", "RS-04"),
    ("espera respuesta", "RS-04"),
    ("orden de compra", "RS-05"),
    ("compra abierta", "RS-05"),
    ("proveedor activo", "RS-06"),
    ("sin enviar", "RS-07"),
    ("listo para enviar", "RS-07"),
    ("en camino", "RS-08"),
    ("sin entregar", "RS-08"),
    ("cupon descuento", "RS-10"),
    ("catalogo producto", "RS-11"),
    ("ventas por mes", "RC-01"),
    ("por categoria", "RC-01"),
    ("top productos", "RC-02"),
    ("mas vendidos", "RC-02"),
    ("menos vendidos", "RC-02"),
    ("comprado vs vendido", "RC-03"),
    ("balanza interna", "RC-03"),
    ("rotacion inventario", "RC-04"),
    ("tiempo de envio", "RC-05"),
    ("dias promedio", "RC-05"),
    ("uso cupones", "RC-06"),
    ("margen categoria", "RC-07"),
    ("ganancia por categoria", "RC-07"),
    ("estado carga datos", "RC-08"),
    ("fact ventas", "RC-08"),
)


def _expand_tokens(text: str) -> set[str]:
    tokens = _tokenize(text)
    expanded = set(tokens)
    for tok in list(tokens):
        for base, syns in _QUERY_SYNONYMS.items():
            if tok == base or tok in syns:
                expanded.add(base)
                expanded.update(syns)
    return expanded


def _intent_boost(prompt: str, report_id: str) -> float:
    text = (prompt or "").lower()
    boost = 0.0
    for phrase, rid in _INTENT_PHRASES:
        if rid == report_id and phrase in text:
            boost += 10.0
    return boost


def _local_reason(*, rep: dict[str, Any], prompt: str, score: float) -> str:
    name = rep.get("name") or rep.get("report_id") or "Informe"
    tipo = rep.get("tipo_label") or ""
    if not (prompt or "").strip():
        return f"{tipo} recomendado para la operación diaria de Altavia Trade." if tipo else "Informe frecuente en el catálogo."
    if score >= 10:
        return f"Tu consulta encaja directamente con «{name}» ({rep.get('id', '')})."
    if score >= 6:
        return f"Relacionado con «{prompt.strip()[:60]}» — revisa {name}."
    return f"Mejor opción disponible en el catálogo para «{prompt.strip()[:50]}»."


def engine_status() -> dict[str, Any]:
    configured = _ai_configured()
    return {
        "ai_available": configured,
        "engine_default": "openai" if configured else "unconfigured",
        "provider": "OpenAI",
        "model": settings.ai_model,
        "engine_note": (
            f"OpenAI Responses API configurada · modelo {settings.ai_model}."
            if configured
            else "La IA no está configurada. Agrega OPENAI_API_KEY al archivo .env y reinicia el servicio."
        ),
    }


def _report_blob(rep: dict[str, Any]) -> str:
    cols = " ".join(rep.get("columns") or [])
    return " ".join(
        [
            str(rep.get("id") or ""),
            str(rep.get("name") or ""),
            str(rep.get("para_que") or ""),
            str(rep.get("quien") or ""),
            cols,
        ]
    ).lower()


def _score_report(rep: dict[str, Any], prompt: str, *, scope: str = SCOPE_ALL) -> float:
    blob = _report_blob(rep)
    tokens = _expand_tokens(prompt)
    if not tokens and not (prompt or "").strip():
        return 0.0
    score = _intent_boost(prompt, str(rep.get("id") or ""))
    if not tokens:
        return score
    for tok in tokens:
        if tok in blob:
            score += 2.0
        elif any(tok in word for word in blob.split()):
            score += 0.75
    # Frases útiles del catálogo
    simple_hints = {
        "stock": ("RS-03",),
        "inventario": ("RS-03",),
        "pago": ("RS-02",),
        "cobro": ("RS-02",),
        "pendiente": ("RS-01", "RS-07", "RS-08"),
        "proveedor": ("RS-05", "RS-06"),
        "compra": ("RS-05",),
        "envio": ("RS-07", "RS-08"),
        "logistica": ("RS-07", "RS-08"),
        "chat": ("RS-04",),
        "soporte": ("RS-04",),
        "cupon": ("RS-10",),
        "producto": ("RS-11",),
        "cliente": ("RS-01", "RS-02"),
        "pedido": ("RS-01", "RS-07"),
    }
    compound_hints = {
        "venta": ("RC-01", "RC-02", "RC-07"),
        "margen": ("RC-07",),
        "categoria": ("RC-01", "RC-07"),
        "ranking": ("RC-02",),
        "top": ("RC-02",),
        "rotacion": ("RC-04",),
        "inventario": ("RC-04",),
        "compra": ("RC-03",),
        "balanza": ("RC-03",),
        "logistica": ("RC-05",),
        "region": ("RC-05",),
        "cupon": ("RC-06",),
        "datos": ("RC-08",),
        "elt": ("RC-08",),
        "modelo": ("RC-08",),
        "estrateg": ("RC-01", "RC-02", "RC-07"),
        "tendencia": ("RC-01",),
        "mes": ("RC-01",),
    }
    hints = compound_hints if scope == SCOPE_COMPOUND else simple_hints if scope == SCOPE_SIMPLE else {**simple_hints, **compound_hints}
    rid = rep.get("id", "")
    for key, ids in hints.items():
        if key in tokens and rid in ids:
            score += 3.0
    if scope == SCOPE_SIMPLE and rep.get("tipo") == SCOPE_SIMPLE:
        score += 1.5
    if scope == SCOPE_COMPOUND and rep.get("tipo") == SCOPE_COMPOUND:
        score += 1.5
    return score


def _local_recommendations(*, prompt: str, limit: int = 5, scope: str = SCOPE_ALL) -> list[dict[str, Any]]:
    scope = normalize_scope(scope)
    catalog = _catalog_entries(scope=scope)
    scored = sorted(
        (
            {
                "report_id": rep["id"],
                "tipo": rep.get("tipo", SCOPE_SIMPLE),
                "tipo_label": rep.get("tipo_label", ""),
                "name": rep.get("name", ""),
                "para_que": rep.get("para_que", ""),
                "score": _score_report(rep, prompt, scope=scope),
            }
            for rep in catalog
        ),
        key=lambda x: (-x["score"], x["report_id"]),
    )
    if not prompt.strip():
        defaults = _COMPOUND_DEFAULTS if scope == SCOPE_COMPOUND else _SIMPLE_DEFAULTS if scope == SCOPE_SIMPLE else _SIMPLE_DEFAULTS[:3] + _COMPOUND_DEFAULTS[:2]
        out: list[dict[str, Any]] = []
        by_id = {r["id"]: r for r in catalog}
        for rid in defaults:
            rep = by_id.get(rid)
            if not rep:
                continue
            reason = (
                "Informe estratégico frecuente para análisis de ventas y KPIs."
                if rep.get("tipo") == SCOPE_COMPOUND
                else "Informe operativo frecuente para la gestión diaria."
            )
            out.append(
                {
                    "report_id": rid,
                    "tipo": rep.get("tipo", SCOPE_SIMPLE),
                    "tipo_label": rep.get("tipo_label", ""),
                    "name": rep.get("name", ""),
                    "para_que": rep.get("para_que", ""),
                    "reason": reason,
                    "confidence": "alta",
                }
            )
        return out[:limit]

    out = []
    for row in scored:
        if row["score"] <= 0:
            continue
        out.append(
            {
                "report_id": row["report_id"],
                "tipo": row["tipo"],
                "tipo_label": row.get("tipo_label", ""),
                "name": row["name"],
                "para_que": row["para_que"],
                "reason": _local_reason(
                    rep={
                        "id": row["report_id"],
                        "name": row["name"],
                        "tipo_label": row.get("tipo_label", ""),
                    },
                    prompt=prompt,
                    score=row["score"],
                ),
                "confidence": "alta" if row["score"] >= 6 else "media",
            }
        )
        if len(out) >= limit:
            break
    if not out and scored:
        top = scored[0]
        out.append(
            {
                "report_id": top["report_id"],
                "tipo": top["tipo"],
                "tipo_label": top.get("tipo_label", ""),
                "name": top["name"],
                "para_que": top["para_que"],
                "reason": "Mejor coincidencia disponible en el catálogo actual.",
                "confidence": "baja",
            }
        )
    return out


def _ai_configured() -> bool:
    return bool((settings.openai_api_key or "").strip())


def _response_output_text(body: dict[str, Any]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("type") == "output_text" and content.get("text"):
                return str(content["text"]).strip()
    raise AIServiceError("empty_response", "La API respondió sin contenido utilizable.")


def _call_llm(*, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any]) -> str:
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise AIServiceError(
            "ai_not_configured",
            "El asistente IA necesita una API key. Configura OPENAI_API_KEY en el archivo .env.",
            http_status=503,
        )
    base = (settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")
    payload = {
        "model": settings.ai_model,
        "instructions": instructions,
        "input": input_text,
        "store": False,
        "max_output_tokens": 1200,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            },
            "verbosity": "low",
        },
    }
    req = urllib.request.Request(
        f"{base}/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=max(10, int(settings.ai_timeout_seconds))) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return _response_output_text(body)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error") or {}
            api_message = str(detail.get("message") or "").strip()
            api_code = str(detail.get("code") or detail.get("type") or "api_error")
        except Exception:
            api_message, api_code = "", "api_error"
        if exc.code in (401, 403):
            message = "La API rechazó la credencial. Revisa OPENAI_API_KEY."
        elif exc.code == 429:
            message = "La API alcanzó su límite de uso o cuota. Revisa la cuenta del proveedor."
        else:
            message = api_message or f"La API devolvió un error HTTP {exc.code}."
        raise AIServiceError(api_code, message, http_status=502) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise AIServiceError("ai_unreachable", "No se pudo conectar con la API de IA dentro del tiempo esperado.", http_status=504) from exc
    except json.JSONDecodeError as exc:
        raise AIServiceError("invalid_api_response", "La API devolvió una respuesta que no se pudo interpretar.") from exc


def _llm_recommendations(*, prompt: str, limit: int = 5, scope: str = SCOPE_ALL) -> list[dict[str, Any]] | None:
    scope = normalize_scope(scope)
    catalog = _catalog_for_llm(scope=scope)
    scope_note = ""
    if scope == SCOPE_SIMPLE:
        scope_note = " Solo informes simples RS (operativos, listados del día a día)."
    elif scope == SCOPE_COMPOUND:
        scope_note = " Solo informes compuestos RC (estratégicos, agregaciones y KPIs)."
    system = (
        "Eres analista de negocio en Altavia Trade. Recomienda informes del catálogo dado."
        + scope_note
        + " Responde SOLO JSON con clave recommendations: lista de objetos "
        "{report_id, reason, confidence} donde confidence es alta|media|baja. "
        "Usa únicamente IDs del catálogo."
    )
    user = json.dumps(
        {"consulta": prompt or "recomienda informes útiles para hoy", "catalogo": catalog, "max": limit},
        ensure_ascii=False,
    )
    raw = _call_llm(
        instructions=system,
        input_text=user,
        schema_name="report_recommendations",
        schema={
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "maxItems": limit,
                    "items": {
                        "type": "object",
                        "properties": {
                            "report_id": {"type": "string"},
                            "reason": {"type": "string"},
                            "confidence": {"type": "string", "enum": ["alta", "media", "baja"]},
                        },
                        "required": ["report_id", "reason", "confidence"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["recommendations"],
            "additionalProperties": False,
        },
    )
    try:
        data = json.loads(raw)
        recs = data.get("recommendations") or []
    except json.JSONDecodeError:
        return None
    by_id = {r["id"]: r for r in _catalog_entries(scope=scope)}
    out: list[dict[str, Any]] = []
    for item in recs:
        rid = str(item.get("report_id") or "").upper()
        rep = by_id.get(rid)
        if not rep:
            continue
        out.append(
            {
                "report_id": rid,
                "tipo": rep.get("tipo", SCOPE_SIMPLE),
                "tipo_label": rep.get("tipo_label", ""),
                "name": rep.get("name", ""),
                "para_que": rep.get("para_que", ""),
                "reason": str(item.get("reason") or "Recomendado por el asistente IA."),
                "confidence": str(item.get("confidence") or "media"),
            }
        )
        if len(out) >= limit:
            break
    return out or None


def recommend_reports(*, prompt: str | None = None, limit: int = 5, scope: str = SCOPE_ALL) -> dict[str, Any]:
    scope = normalize_scope(scope)
    text = (prompt or "").strip()
    if not _ai_configured():
        raise AIServiceError("ai_not_configured", "Configura OPENAI_API_KEY para utilizar el asistente IA.", http_status=503)
    recs = _llm_recommendations(prompt=text, limit=limit, scope=scope) or []
    catalog_info = list_ai_catalog(scope=scope)
    status = engine_status()
    return {
        "engine": "openai",
        "ai_available": status["ai_available"],
        "engine_note": status["engine_note"],
        "scope": scope,
        "scope_meta": SCOPE_META.get(scope) if scope != SCOPE_ALL else None,
        "catalog_counts": catalog_info["counts"],
        "prompt": text or None,
        "recommendations": recs,
    }


def _extract_search_query(prompt: str) -> str | None:
    quoted = re.search(r"[\"']([^\"']{2,80})[\"']", prompt)
    if quoted:
        return quoted.group(1).strip()
    m = re.search(r"\b(?:cliente|producto|proveedor|correo|sku)\s+([a-z0-9@._-]{2,40})", prompt, re.I)
    if m:
        return m.group(1).strip()
    return None


def _custom_title(prompt: str, fallback: str) -> str:
    text = (prompt or "").strip()
    if not text:
        return fallback
    cleaned = re.sub(r"\s+", " ", text)
    if len(cleaned) > 90:
        cleaned = cleaned[:87].rstrip() + "…"
    return cleaned[0].upper() + cleaned[1:] if cleaned else fallback


def _llm_pick_report(prompt: str, *, scope: str = SCOPE_ALL) -> dict[str, Any] | None:
    scope = normalize_scope(scope)
    catalog = _catalog_for_llm(scope=scope)
    scope_note = ""
    if scope == SCOPE_SIMPLE:
        scope_note = " Debes elegir solo un informe simple RS (operativo)."
    elif scope == SCOPE_COMPOUND:
        scope_note = " Debes elegir solo un informe compuesto RC (estratégico)."
    system = (
        "Elige el informe del catálogo Altavia Trade que mejor responde la petición del usuario."
        + scope_note
        + " Responde SOLO JSON: "
        "{report_id, custom_name, search_query, reason, narrative} "
        "donde report_id es RS-xx o RC-xx del catálogo, custom_name en español, "
        "search_query opcional solo para informes simples con filtro de texto, "
        "narrative es un párrafo breve en español explicando qué muestra el informe."
    )
    user = json.dumps({"peticion": prompt, "catalogo": catalog}, ensure_ascii=False)
    raw = _call_llm(
        instructions=system,
        input_text=user,
        schema_name="report_selection",
        schema={
            "type": "object",
            "properties": {
                "report_id": {"type": "string"},
                "custom_name": {"type": "string"},
                "search_query": {"type": ["string", "null"]},
                "reason": {"type": "string"},
                "narrative": {"type": "string"},
            },
            "required": ["report_id", "custom_name", "search_query", "reason", "narrative"],
            "additionalProperties": False,
        },
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _local_narrative(*, prompt: str, report: dict[str, Any], total: int) -> str:
    name = report.get("name") or report.get("id") or "Informe"
    para = report.get("para_que") or ""
    if total:
        return (
            f"Se generó «{name}» a partir de tu petición. "
            f"{para} Se encontraron {total} fila{'s' if total != 1 else ''}."
        )
    return (
        f"Se generó «{name}». {para} "
        "No hay filas con los criterios actuales; prueba ampliar filtros o ejecutar la carga ELT."
    )


def generate_report_from_prompt(
    *,
    prompt: str,
    limit: int = 100,
    threshold: int = 20,
    scope: str = SCOPE_ALL,
) -> dict[str, Any]:
    scope = normalize_scope(scope)
    text = (prompt or "").strip()
    if not text:
        raise ValueError("prompt_required")

    if not _ai_configured():
        raise AIServiceError("ai_not_configured", "Configura OPENAI_API_KEY para utilizar el asistente IA.", http_status=503)
    engine = "openai"
    pick = _llm_pick_report(text, scope=scope)
    if not pick:
        raise AIServiceError("invalid_selection", "La IA no pudo seleccionar un informe válido.")

    rid = str(pick.get("report_id") or "").upper()
    catalog = {r["id"]: r for r in _catalog_entries(scope=scope)}
    meta = catalog.get(rid)
    if not meta:
        raise ValueError("unknown_report")

    q = (pick.get("search_query") or _extract_search_query(text) or "").strip() or None
    tipo = meta.get("tipo", SCOPE_SIMPLE)
    if tipo == SCOPE_COMPOUND:
        data = compuestos.run_complex_report(rid, limit=limit)
        q = None
    else:
        data = services.run_report(rid, q=q, limit=limit, threshold=threshold)

    report = dict(data.get("report") or {})
    custom_name = str(pick.get("custom_name") or "").strip() or _custom_title(text, report.get("name", rid))
    report["name"] = custom_name
    report["ai_generated"] = True
    report["source_report_id"] = rid
    report["tipo"] = tipo
    report["tipo_label"] = meta.get("tipo_label", "")

    total = int(data.get("total") or len(data.get("rows") or []))
    narrative = pick.get("narrative") or _local_narrative(prompt=text, report=report, total=total)

    status = engine_status()
    return {
        "engine": engine,
        "ai_available": status["ai_available"],
        "engine_note": status["engine_note"],
        "scope": scope,
        "scope_meta": SCOPE_META.get(scope) if scope != SCOPE_ALL else None,
        "prompt": text,
        "matched_report_id": rid,
        "match_reason": pick.get("reason") or "",
        "narrative": narrative,
        "search_query": q,
        "report": report,
        "rows": data.get("rows") or [],
        "total": total,
        "message": data.get("message"),
        "threshold": data.get("threshold"),
        "tipo": tipo,
        "tipo_label": meta.get("tipo_label", ""),
    }
