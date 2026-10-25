"""Safety and functional coverage for the manager-reviewed learning loop."""
import asyncio
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import main
from app.expertise import (
    KnowledgeBase, contains_sensitive, matching_guides, reference_for, domain_demo_reply
)
from app.services import AIService
from app.settings import Settings


def test_industry_guide_has_architecture_estimates_design_and_supervision():
    assert matching_guides("Смета ва ведомости ҳаҷми корҳо")
    assert "Смета" in reference_for("сметаи сохтмон")
    assert "назорати муаллифӣ" in reference_for("назорати муаллифӣ").casefold()
    assert "дизайни дохилӣ" in reference_for("дизайни дохилӣ")
    assert "architect" not in (domain_demo_reply("смета", True) or "").casefold()


def test_review_required_and_only_approved_knowledge_is_searchable(tmp_path):
    db = KnowledgeBase(str(tmp_path / "knowledge.db"))
    idx = db.propose("Сметаи дизайн чӣ гуна таҳия мешавад?",
                     "Барои смета аввал ведомости ҳаҷми кор ва нақшаҳои лоиҳа заруранд.",
                     "estimate")
    assert db.list_entries("pending")[0]["id"] == idx
    assert db.search_approved("смета дизайн") == []
    db.review(idx, "approved")
    answers = db.search_approved("смета дизайн")
    assert answers and answers[0]["answer"].startswith("Барои смета")
    assert "MANAGER-APPROVED" in db.context("смета дизайн")
    db.review(idx, "rejected")
    assert db.search_approved("смета дизайн") == []


def test_private_data_is_not_learned(tmp_path):
    db = KnowledgeBase(str(tmp_path / "private.db"))
    assert contains_sensitive("Call +992 900 11 88 15")
    assert contains_sensitive("Write me@example.com")
    assert db.suggest_from_staff("Телефони ман +992 900 11 88 15 аст",
                                  "Ҳоло занг мезанем.") is None
    assert db.list_entries() == []
    with pytest.raises(ValueError):
        db.propose("Email адреси шумо чист?", "Ба test@example.com нависед.")


def test_staff_reply_creates_pending_proposal_not_approved(tmp_path, monkeypatch):
    settings=replace(Settings(),database_path=str(tmp_path/"app.db"),demo_mode=True,
                     ai_preview_mode=False,suggest_from_staff=True,
                     admin_username="plazai",admin_password="test-staff-password")
    monkeypatch.setattr(main,"config",settings)
    auth=("plazai","test-staff-password")
    hdr={"X-PLAZAI-Request":"dashboard"}
    with TestClient(main.app) as client:
        assert client.get("/api/admin/knowledge").status_code == 401
        client.post("/api/admin/demo",auth=auth,headers=hdr,
                    json={"text":"Смета ба кадом ҳуҷҷатҳо асос меёбад?"})
        client.post("/api/admin/chats/992900000001/mode",auth=auth,headers=hdr,
                    json={"mode":"human"})
        reply=client.post("/api/admin/chats/992900000001/reply",auth=auth,headers=hdr,
                    json={"text":"Смета аз нақшаҳо ва ҳаҷми корҳои ҳисобшуда таҳия мегардад."})
        assert reply.status_code == 200
        items=client.get("/api/admin/knowledge",auth=auth).json()["items"]
        assert len(items)==1 and items[0]["state"]=="pending"
        assert client.post("/api/admin/knowledge/"+str(items[0]["id"])+"/review",
                           json={"state":"approved"},auth=auth).status_code==403
        approved=client.post("/api/admin/knowledge/"+str(items[0]["id"])+"/review",
                             json={"state":"approved"},auth=auth,headers=hdr)
        assert approved.status_code==200
        assert main.knowledge.search_approved("Смета ба кадом ҳуҷҷатҳо") != []


def test_model_is_grounded_only_in_manager_approved_information(tmp_path):
    kb=KnowledgeBase(str(tmp_path/"model.db"))
    idx=kb.propose("Чӣ гуна смета месозанд?",
                   "Смета аз ведомости ҳаҷми корҳо ва нархҳои санҷидашуда тартиб мешавад.")
    kb.review(idx,"approved")
    class DummyReply:
        def raise_for_status(self): pass
        def json(self):
            return {"output":[{"type":"message","content":[{"type":"output_text","text":"Маълумотро бояд санҷид."}]}]}
    class DummyClient:
        def __init__(self): self.body=None
        async def post(self,uri,headers,json):
            self.body=json
            return DummyReply()
    service=AIService("local-test-key","test-model")
    fake=DummyClient()
    service.client=fake
    service.knowledge_provider=kb.context
    reply=asyncio.run(service.reply([{"role":"user","body":"Чӣ гуна смета месозанд?"}]))
    assert reply=="Маълумотро бояд санҷид."
    assert "MANAGER-APPROVED" in fake.body["instructions"]
    assert "Смета аз ведомости" in fake.body["instructions"]
    assert fake.body["store"] is False
