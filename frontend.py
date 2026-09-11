from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
st.set_page_config(page_title="Открой Хабаровский край", page_icon="🌊", layout="wide")
st.markdown(
    """
    <style>
    :root { --khv-blue:#075985; --khv-sky:#0ea5e9; --khv-sand:#f5efe3; }
    .stApp { background:linear-gradient(180deg,#eef9ff 0,#fff 340px); }
    h1,h2,h3 { color:#0c4a6e; }
    [data-testid="stMetric"] { background:white;border:1px solid #bae6fd;border-radius:16px;padding:14px; }
    .hero {padding:28px;border-radius:24px;background:linear-gradient(120deg,#075985,#0ea5e9);color:white;margin-bottom:18px}
    .hero h1,.hero p {color:white;margin:0}.hero p{margin-top:8px;opacity:.9}
    </style>
    <div class="hero"><h1>Открой Хабаровский край</h1><p>Узнавайте места по фотографии и собирайте собственный маршрут по Дальнему Востоку.</p></div>
    """,
    unsafe_allow_html=True,
)


def headers() -> dict[str, str]:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api(method: str, path: str, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            headers={**headers(), **kwargs.pop("headers", {})},
            timeout=70,
            **kwargs,
        )
        if response.status_code >= 400:
            detail = (
                response.json().get("detail", response.text)
                if response.content
                else response.reason
            )
            st.error(f"API {response.status_code}: {detail}")
            return None
        return response.json()
    except requests.RequestException as error:
        st.error(f"Сервер недоступен: {error}")
        return None


recognition, catalog, route, account, admin = st.tabs(
    ["📷 Распознать", "🗺️ Каталог", "🧭 Маршрут", "👤 Аккаунт", "⚙️ Администратор"]
)

with recognition:
    st.subheader("Что перед вами?")
    image = st.file_uploader(
        "Перетащите фотографию или выберите файл", type=["jpg", "jpeg", "png", "webp"]
    )
    if image:
        left, right = st.columns([1, 1])
        with left:
            st.image(image, use_container_width=True)
        with right:
            if st.button("Распознать место", type="primary", use_container_width=True):
                with st.spinner("Сопоставляем фотографию с коллекцией…"):
                    result = api(
                        "POST",
                        "/api/recognize",
                        files={"file": (image.name, image.getvalue(), image.type)},
                    )
                if result and result.get("recognized"):
                    item = result["object"]
                    st.success(item["name"])
                    st.metric("Уверенность", f"{result['confidence'] * 100:.1f}%")
                    st.write(item["description"])
                    st.caption(f"{item['municipality']} · {item.get('address', '')}")
                    if item.get("access_notes"):
                        st.info(item["access_notes"])
                elif result:
                    st.warning("Не удалось распознать объект уверенно. Попробуйте другой ракурс.")
                    if result.get("top_matches"):
                        st.caption(
                            "Ближайшие варианты: "
                            + ", ".join(match["name"] for match in result["top_matches"][:3])
                        )

with catalog:
    payload = api("GET", "/api/objects")
    objects = payload.get("objects", []) if payload else []
    categories = sorted({item["category"] for item in objects})
    selected = st.multiselect("Категории", categories)
    query = st.text_input("Поиск по названию или району")
    shown = [
        item
        for item in objects
        if (not selected or item["category"] in selected)
        and (not query or query.lower() in f"{item['name']} {item['municipality']}".lower())
    ]
    st.caption(f"Найдено: {len(shown)}")
    for start in range(0, len(shown), 3):
        columns = st.columns(3)
        for column, item in zip(columns, shown[start : start + 3], strict=False):
            with column:
                if item.get("example_images"):
                    st.image(f"{API_BASE_URL}{item['example_images'][0]}", use_container_width=True)
                st.markdown(f"### {item['name']}")
                st.caption(f"{item['municipality']} · {item['category']}")
                st.write(item["description"])

with route:
    st.subheader("Маршрут от вашей точки")
    c1, c2, c3 = st.columns(3)
    latitude = c1.number_input("Широта", value=48.4800, format="%.6f")
    longitude = c2.number_input("Долгота", value=135.0710, format="%.6f")
    limit = c3.slider("Количество мест", 1, 15, 7)
    if st.button("Построить маршрут", type="primary"):
        result = api(
            "POST",
            "/api/plan-route",
            json={"latitude": latitude, "longitude": longitude, "limit": limit},
        )
        if result:
            st.metric("Оценочная длина", f"{result['total_distance_km']:.1f} км")
            for index, item in enumerate(result["route"], 1):
                st.write(
                    f"**{index}. {item['name']}** — {item['distance_from_previous_km']:.1f} км"
                )

with account:
    if st.session_state.get("token"):
        me = api("GET", "/auth/me")
        if me:
            st.success(f"Вы вошли как {me['email']} ({me['role']})")
        if st.button("Выйти"):
            api("POST", "/auth/logout")
            st.session_state.pop("token", None)
            st.rerun()
        history = api("GET", "/auth/me/recognized") or []
        st.subheader("История распознаваний")
        for item in history:
            st.write(
                f"{item.get('object_name') or 'Неизвестный объект'} · {item['confidence'] * 100:.1f}%"
            )
    else:
        login_tab, register_tab = st.tabs(["Вход", "Регистрация"])
        with login_tab, st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Пароль", type="password")
            if st.form_submit_button("Войти", type="primary"):
                result = api("POST", "/auth/login", json={"email": email, "password": password})
                if result:
                    st.session_state.token = result["access_token"]
                    st.rerun()
        with register_tab, st.form("register"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Пароль от 10 символов", type="password", key="reg_password")
            if st.form_submit_button("Создать аккаунт"):
                result = api("POST", "/auth/register", json={"email": email, "password": password})
                if result:
                    st.success("Аккаунт создан — теперь войдите.")

with admin:
    me = api("GET", "/auth/me") if st.session_state.get("token") else None
    if not me or me.get("role") != "admin":
        st.info("Войдите под административной учётной записью.")
    else:
        stats = api("GET", "/api/stats")
        if stats:
            c1, c2, c3 = st.columns(3)
            c1.metric("Объекты", stats["objects"])
            c2.metric("Примеры", stats["images"])
            c3.metric("Индекс", "Готов" if stats["index_ready"] else "Требует сборки")
        if st.button("Перестроить индекс", type="primary"):
            result = api("POST", "/api/admin/reindex")
            if result:
                st.success("Индексация запущена в фоне.")
        st.subheader("Добавить объект")
        with st.form("add-object"):
            name = st.text_input("Название")
            category_name = st.text_input("Категория", value="architecture")
            municipality = st.text_input("Город или район")
            address = st.text_input("Адрес")
            description = st.text_area("Описание")
            files = st.file_uploader(
                "Фотографии", type=["jpg", "jpeg", "png"], accept_multiple_files=True
            )
            if st.form_submit_button("Сохранить"):
                multipart = [("images", (file.name, file.getvalue(), file.type)) for file in files]
                result = api(
                    "POST",
                    "/api/objects",
                    data={
                        "name": name,
                        "category": category_name,
                        "municipality": municipality,
                        "address": address,
                        "description": description,
                    },
                    files=multipart,
                )
                if result:
                    st.success("Объект добавлен. Для распознавания перестройте индекс.")
