from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from mail_bridge.classifier import build_classifier
from mail_bridge.config import get_settings
from mail_bridge.gmail import GmailClient
from mail_bridge.notifier import build_notifier
from mail_bridge.preferences import PreferenceAction, PreferenceScope, build_preference_note
from mail_bridge.pubsub_subscriber import PubSubStreamingSubscriber
from mail_bridge.rules import RulesStore
from mail_bridge.service import MailBridgeService
from mail_bridge.store import StateStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger(__name__)


class PreferenceNoteCreateRequest(BaseModel):
    note: str = Field(min_length=1, max_length=280)


class PreferencesResponse(BaseModel):
    policy_note: str
    notes: list[str]


class PreferenceRuleCreateRequest(BaseModel):
    scope: PreferenceScope
    value: str = Field(min_length=1, max_length=80)
    action: PreferenceAction
    reason: str | None = Field(default=None, max_length=120)


class PreferenceRuleCreateResponse(PreferencesResponse):
    note: str


def build_application() -> FastAPI:
    settings = get_settings()
    rules_store = RulesStore(settings.memento_rules_file, settings.importance_policy_note)
    rules_store.ensure_exists()
    store = StateStore(settings.state_db_path)
    gmail_client = GmailClient(settings)
    classifier = build_classifier(settings, rules_store)
    notifier = build_notifier(settings)
    service = MailBridgeService(settings, store, gmail_client, classifier, notifier)
    pubsub_subscriber = PubSubStreamingSubscriber(settings, service)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        renew_task = asyncio.create_task(periodic_watch_renewal(service, settings.gmail_watch_check_interval_minutes))
        try:
            pubsub_subscriber.start()
            try:
                await asyncio.to_thread(service.renew_watch_if_needed, False)
            except Exception as error:
                LOGGER.warning("initial watch renewal skipped: %s", error)
            yield
        finally:
            renew_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await renew_task
            pubsub_subscriber.stop()

    app = FastAPI(title="mail-bridge", lifespan=lifespan)
    app.state.mail_bridge_service = service

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/watch/status")
    async def watch_status() -> dict[str, object]:
        status = await asyncio.to_thread(service.get_watch_status)
        status["pubsub_mode"] = settings.pubsub_mode
        status["pubsub_subscription_name"] = settings.pubsub_subscription_name
        return status

    @app.get("/preferences", response_model=PreferencesResponse)
    async def preferences() -> PreferencesResponse:
        rules = await asyncio.to_thread(rules_store.load)
        return PreferencesResponse(policy_note=rules.policy_note, notes=rules.notes)

    @app.post("/preferences/notes", response_model=PreferencesResponse)
    async def add_preference_note(payload: PreferenceNoteCreateRequest) -> PreferencesResponse:
        try:
            rules = await asyncio.to_thread(rules_store.add_note, payload.note)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return PreferencesResponse(policy_note=rules.policy_note, notes=rules.notes)

    @app.post("/preferences/rules", response_model=PreferenceRuleCreateResponse)
    async def add_preference_rule(payload: PreferenceRuleCreateRequest) -> PreferenceRuleCreateResponse:
        try:
            note = build_preference_note(
                scope=payload.scope,
                value=payload.value,
                action=payload.action,
                reason=payload.reason,
            )
            rules = await asyncio.to_thread(rules_store.add_note, note)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return PreferenceRuleCreateResponse(
            note=note,
            policy_note=rules.policy_note,
            notes=rules.notes,
        )

    @app.post("/watch/renew")
    async def watch_renew() -> dict[str, object]:
        try:
            state = await asyncio.to_thread(service.renew_watch_if_needed, True)
            return {
                "email": state.email,
                "cursor_history_id": state.cursor_history_id,
                "watch_history_id": state.watch_history_id,
                "expiration_epoch_ms": state.expiration_epoch_ms,
            }
        except Exception as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.post("/pubsub/push")
    async def pubsub_push(
        envelope: dict[str, object],
        authorization: str | None = Header(default=None),
    ) -> dict[str, object]:
        try:
            outcome = await asyncio.to_thread(service.handle_pubsub_push, envelope, authorization)
        except PermissionError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except Exception as error:
            LOGGER.exception("failed to process pubsub push")
            raise HTTPException(status_code=500, detail=str(error)) from error
        return {
            "processed_count": outcome.processed_count,
            "notified_count": outcome.notified_count,
            "latest_history_id": outcome.latest_history_id,
        }

    return app


async def periodic_watch_renewal(service: MailBridgeService, interval_minutes: int) -> None:
    while True:
        try:
            await asyncio.to_thread(service.renew_watch_if_needed, False)
        except Exception as error:
            LOGGER.warning("watch renewal loop failed: %s", error)
        await asyncio.sleep(max(60, interval_minutes * 60))


app = build_application()
