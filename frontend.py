from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8100").rstrip("/")
st.set_page_config(page_title="Открой Хабаровский край", page_icon="🌊", layout="wide")
st.markdown(
    """
    <style>
    :root { --amur:#0B4F7C; --amur-dark:#073654; --sky:#E8F3FA; --gold:#C8962E; --gold-soft:#FBF3E0;
            --ink:#14212B; --muted:#5A6B78; --line:#D9E4EC; --ok:#1E7A4F; --warn:#B06A12; --bad:#B3261E; }
    .stApp { background:#F6F9FB; }
    h1,h2,h3 { color:var(--amur-dark); letter-spacing:-.01em; }
    [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); border-radius:14px; padding:12px 14px; }
    [data-testid="stMetricLabel"] { color:var(--muted); }
    .stTabs [data-baseweb="tab-list"] { gap:6px; border-bottom:1px solid var(--line); }
    .stTabs [data-baseweb="tab"] { padding:10px 14px; border-radius:10px 10px 0 0; }
    .stTabs [aria-selected="true"] { color:var(--amur) !important; }
    .hero { padding:20px 24px; border-radius:18px; background:linear-gradient(120deg,var(--amur-dark),var(--amur));
            color:#fff; margin-bottom:12px; border-bottom:4px solid var(--gold); }
    .hero h1 { color:#fff; margin:0; font-size:1.7rem; }
    .hero p { color:#DCEBF5; margin:6px 0 0; }
    .status-row { display:flex; flex-wrap:wrap; gap:8px; margin:4px 0 14px; }
    .pill { display:inline-flex; align-items:center; gap:6px; padding:6px 12px; border-radius:999px; font-size:.86rem;
            background:#fff; border:1px solid var(--line); color:var(--ink); }
    .dot { width:9px; height:9px; border-radius:50%; display:inline-block; }
    .ok { background:var(--ok); } .warn { background:var(--warn); } .bad { background:var(--bad); }
    .meta { color:var(--muted); font-size:.88rem; }
    .chip { display:inline-block; background:var(--sky); color:var(--amur-dark); border-radius:999px; padding:2px 10px;
            font-size:.8rem; margin:2px 4px 2px 0; }
    .chip.gold { background:var(--gold-soft); color:#7A5712; }
    </style>
    <div class="hero"><h1>Открой Хабаровский край</h1>
    <p>Панель стенда v3: распознавание, каталог, маршруты и администрирование.</p></div>
    """,
    unsafe_allow_html=True,
)


def headers() -> dict[str, str]:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api(method: str, path: str, quiet: bool = False, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{path}",
            headers={**headers(), **kwargs.pop("headers", {})},
            timeout=kwargs.pop("timeout", 70),
            **kwargs,
        )
        if response.status_code >= 400:
            detail = (
                response.json().get("detail", response.text)
                if response.content
                else response.reason
            )
            if not quiet:
                st.error(f"API {response.status_code}: {detail}")
            return None
        return response.json()
    except requests.RequestException as error:
        if not quiet:
            st.error(f"Сервер недоступен: {error}")
        return None


def pill(level: str, text: str) -> str:
    return f'<span class="pill"><span class="dot {level}"></span>{text}</span>'


health = api("GET", "/health", quiet=True, timeout=8)
if health is None:
    pills = [pill("bad", f"API недоступен · {API_BASE_URL}")]
else:
    kb = health.get("knowledge_base", {})
    guide = health.get("assistant", {})
    pills = [
        pill("ok", f"API работает · v{health.get('version', '?')}"),
        pill("ok", "Индекс распознавания готов")
        if health.get("index_ready")
        else pill("bad", f"Индекс не готов: {health.get('index_reason') or 'нет данных'}"),
        pill("ok", f"База знаний {kb.get('version', '')} · {kb.get('places', 0)} мест")
        if kb.get("ready")
        else pill("bad", f"База знаний не готова {kb.get('error', '')}"),
        pill("ok", f"ИИ-гид: {guide.get('model')}")
        if guide.get("llm_available")
        else pill("warn", "ИИ-гид в резервном режиме (ответы из базы)"),
    ]
    if health.get("status") != "ready":
        pills.append(pill("warn", "Качество распознавания ниже порога релиза"))
st.markdown(f'<div class="status-row">{"".join(pills)}</div>', unsafe_allow_html=True)


recognition, catalog, route, account, admin = st.tabs(
    ["Распознать", "Каталог", "Маршрут", "Аккаунт", "Администратор"]
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
                    st.write(item.get("short_description") or item["description"])
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
            with column, st.container(border=True):
                if item.get("example_images"):
                    st.image(f"{API_BASE_URL}{item['example_images'][0]}", use_container_width=True)
                st.markdown(f"**{item['name']}**")
                st.markdown(
                    f'<div class="meta">{item["municipality"]} · {item["category"]}</div>'
                    f'<span class="chip">{item.get("best_months_label") or "сезон не указан"}</span>'
                    f'<span class="chip">{item.get("visit_label") or "—"}</span>'
                    f'<span class="chip gold">{item.get("difficulty_label") or "—"}</span>',
                    unsafe_allow_html=True,
                )
                st.write(item.get("short_description") or item["description"])

with route:
    st.subheader("Маршрут от вашей точки")
    c1, c2, c3, c4 = st.columns(4)
    latitude = c1.number_input("Широта", value=48.4800, format="%.6f")
    longitude = c2.number_input("Долгота", value=135.0710, format="%.6f")
    limit = c3.slider("Количество мест", 1, 15, 7)
    mode_label = c4.radio("Передвижение", ["Пешком", "Автомобиль"], horizontal=True)
    if st.button("Построить маршрут", type="primary"):
        result = api(
            "POST",
            "/api/plan-route",
            json={
                "latitude": latitude,
                "longitude": longitude,
                "limit": limit,
                "travel_mode": "walk" if mode_label == "Пешком" else "car",
            },
        )
        if result:
            summary = result.get("summary", {})
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Расстояние по прямой", f"{result['total_distance_km']:.1f} км")
            m2.metric("В пути", f"{summary.get('travel_minutes', 0)} мин")
            m3.metric("На осмотр", f"{summary.get('visit_minutes', 0)} мин")
            m4.metric("Всего", f"{summary.get('total_minutes', 0)} мин")
            for warning in result.get("warnings", []):
                st.warning(warning)
            for item in result["route"]:
                leg = item.get("leg") or {}
                st.write(
                    f"**{item['order']}. {item['name']}** — {leg.get('estimated_road_km', 0)} км, "
                    f"~{leg.get('travel_minutes', 0)} мин в пути, осмотр ~{item['visit_minutes']['planned']} мин"
                )
            st.caption(result.get("estimation", {}).get("description", ""))

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
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Объекты", stats["objects"])
            c2.metric("Примеры", stats["images"])
            c3.metric("Индекс", "Готов" if stats["index_ready"] else "Требует сборки")
            kb = stats.get("knowledge_base", {})
            c4.metric("База знаний", f"{kb.get('places', 0)} мест", kb.get("version", ""))
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
