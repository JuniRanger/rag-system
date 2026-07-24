from app.rag.schemas import RAGUser, UsuarioInfo
from app.rag.tool_loop import _inject_cita_usuario, _strip_tool_json_leak
from app.tools.implementations.citas import _normalize_usuario, _sanitize_api_body_for_llm


def test_cita_usuario_payload_maps_email_to_correo():
    user = RAGUser(
        id="1",
        usuario=UsuarioInfo(nombre="Cliente Guapo", email="levos@gmail.com"),
    )
    assert user.cita_usuario_payload() == {
        "id": "1",
        "nombre": "Cliente Guapo",
        "correo": "levos@gmail.com",
    }


def test_cita_usuario_payload_prefers_correo():
    user = RAGUser(
        id="1",
        usuario=UsuarioInfo(
            nombre="Cliente Guapo",
            correo="levos@gmail.com",
            email="otro@gmail.com",
        ),
    )
    assert user.cita_usuario_payload()["correo"] == "levos@gmail.com"


def test_normalize_usuario_accepts_email_alias():
    assert _normalize_usuario(
        {"id": "1", "nombre": "Cliente Guapo", "email": "levos@gmail.com"}
    ) == {"id": "1", "nombre": "Cliente Guapo", "correo": "levos@gmail.com"}


def test_inject_cita_usuario_overwrites_llm_usuario():
    injected = _inject_cita_usuario(
        {
            "fecha": "2026-07-20 15:00",
            "vehiculo": "Mazda 3 2018",
            "producto": "Balatas",
            "usuario": {"id": "fake", "nombre": "Inventado", "correo": "x@y.com"},
            "extra": "ignored",
        },
        {"id": "1", "nombre": "Cliente Guapo", "correo": "levos@gmail.com"},
    )
    assert injected == {
        "fecha": "2026-07-20 15:00",
        "vehiculo": "Mazda 3 2018",
        "producto": "Balatas",
        "usuario": {
            "id": "1",
            "nombre": "Cliente Guapo",
            "correo": "levos@gmail.com",
        },
    }


def test_strip_tool_json_leak_blocks_raw_json():
    leaked = '{"fecha": "2026-07-20 10:00", "vehiculo": "Mazda 3", "producto": "Balatas"}'
    assert "{" not in _strip_tool_json_leak(leaked)


def test_sanitize_api_body_strips_record_ids():
    sanitized = _sanitize_api_body_for_llm(
        {
            "id": 42,
            "cita_id": "uuid-123",
            "fecha": "2026-08-01 09:00",
            "vehiculo": "Mazda 3",
            "producto": "Balatas",
            "usuario_id": 7,
        }
    )
    assert "42" not in sanitized
    assert "uuid-123" not in sanitized
    assert "usuario_id" not in sanitized
    assert "Mazda 3" in sanitized
    assert "Balatas" in sanitized
