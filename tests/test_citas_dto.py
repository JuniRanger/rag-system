from app.rag.schemas import RAGUser, UsuarioInfo
from app.rag.tool_loop import _inject_cita_usuario, _strip_tool_json_leak
from app.tools.implementations.citas import _normalize_usuario


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
