import pytest

from app.rag.memory import SUMMARY_REFRESH_INTERVAL, should_refresh_summary
from app.rag.schemas import ChatMessage, RAGRequest


def test_should_refresh_summary_every_third_user_message():
    request = RAGRequest(
        user_message_count=3,
        message=ChatMessage(role="user", content="tercera pregunta"),
    )
    assert should_refresh_summary(request) is True


def test_should_not_refresh_summary_on_other_messages():
    request = RAGRequest(
        user_message_count=2,
        message=ChatMessage(role="user", content="segunda pregunta"),
    )
    assert should_refresh_summary(request) is False


def test_user_message_index_inferred_from_recent_messages():
    request = RAGRequest(
        recent_messages=[
            ChatMessage(role="user", content="hola"),
            ChatMessage(role="assistant", content="hola, ¿en qué ayudo?"),
        ],
        message=ChatMessage(role="user", content="segunda pregunta"),
    )
    assert request.current_user_message_index() == 2
    assert should_refresh_summary(request) is False


def test_user_message_index_respects_explicit_count():
    request = RAGRequest(
        user_message_count=6,
        message=ChatMessage(role="user", content="sexta pregunta"),
    )
    assert request.current_user_message_index() == 6
    assert should_refresh_summary(request) is True


def test_summary_refresh_interval_is_three():
    assert SUMMARY_REFRESH_INTERVAL == 3
