"""Metas y comisiones transparentes para vendedores."""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Any
from shared.audit import log_audit
from shared.mongo import get_db

def save_goal(data: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    seller = str(data.get("seller_email") or "").strip().lower()
    start, end = str(data.get("period_start") or "")[:10], str(data.get("period_end") or "")[:10]
    target, rate = float(data.get("target") or 0), float(data.get("commission_rate") or 0)
    if not seller or target <= 0 or rate < 0 or rate > 100 or not start or not end or start > end:
        raise ValueError("invalid_sales_goal")
    db = get_db(); last=db["sales_goals"].find_one({}, {"goal_id":1}, sort=[("goal_id",-1)])
    row={"goal_id":int((last or {}).get("goal_id") or 0)+1,"seller_email":seller,"period_start":start,"period_end":end,
         "target":round(target,2),"commission_rate":round(rate,2),"created_at":datetime.now(timezone.utc).isoformat()}
    db["sales_goals"].insert_one(row); row.pop("_id",None)
    log_audit("sales_goal_saved",entity="sales_goals",entity_id=row["goal_id"],details={**row,"actor":actor})
    return row

def overview() -> list[dict[str, Any]]:
    db=get_db(); out=[]
    for goal in db["sales_goals"].find({}, {"_id":0}).sort("goal_id",-1).limit(200):
        q={"$or":[{"reviewed_by":goal["seller_email"]},{"admin_email":goal["seller_email"]}],
           "status":{"$in":["convertida","enviada","entregada","devolucion_parcial","devuelta"]},
           "created_at":{"$gte":goal["period_start"],"$lte":goal["period_end"]+"T23:59:59"}}
        rows=list(db["purchase_requests"].find(q,{"total":1,"return_refund_amount":1,"_id":0}))
        sales=round(sum(max(float(x.get("total") or 0)-float(x.get("return_refund_amount") or 0),0) for x in rows),2)
        out.append({**goal,"sales":sales,"progress":round(sales/float(goal["target"])*100,1),
                    "commission":round(sales*float(goal["commission_rate"])/100,2),"orders":len(rows)})
    return out

def save_usability_feedback(data: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    score=int(data.get("score") or 0); comment=str(data.get("comment") or "").strip()
    if score not in range(1,6): raise ValueError("invalid_usability_feedback")
    row={"score":score,"comment":comment[:500],"completed_steps":list(data.get("completed_steps") or []),
         "actor":actor,"created_at":datetime.now(timezone.utc).isoformat()}
    get_db()["usability_feedback"].insert_one(row); row.pop("_id",None); return row
