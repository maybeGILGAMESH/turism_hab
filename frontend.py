"""
Streamlit frontend for North Caucasus Tourist Attractions Recognition System.

Provides visitor recognition, itinerary planning, admin management,
and system statistics with authentication support.

Факультет Искусственного Интеллекта РУДН
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from PIL import Image

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ---------------------------------------------------------------------------
# Session state & helpers
# ---------------------------------------------------------------------------
def init_session_state() -> None:
    if "auth" not in st.session_state:
        st.session_state["auth"] = {"token": None, "username": None, "role": None}
    if "recognized_history" not in st.session_state:
        st.session_state["recognized_history"] = []
    if "route_results" not in st.session_state:
        st.session_state["route_results"] = None


def get_auth_headers() -> Dict[str, str]:
    token = st.session_state["auth"].get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def is_authenticated() -> bool:
    return bool(st.session_state["auth"].get("token"))


def is_admin() -> bool:
    return st.session_state["auth"].get("role") == "admin"


def auth_api_request(method: str, endpoint: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.update(get_auth_headers())
    return requests.request(method, f"{API_BASE_URL}{endpoint}", headers=headers, **kwargs)


# ---------------------------------------------------------------------------
# Authentication UI
# ---------------------------------------------------------------------------
def handle_auth_sidebar() -> None:
    st.sidebar.title("🏔️ Северный Кавказ")
    st.sidebar.markdown("Система распознавания туристических достопримечательностей")
    st.sidebar.markdown("**Факультет Искусственного Интеллекта РУДН**")

    if is_authenticated():
        username = st.session_state["auth"]["username"]
        role = st.session_state["auth"]["role"]
        st.sidebar.success(f"Вы вошли как **{username}** ({role})")
        if st.sidebar.button("Выйти"):
            try:
                auth_api_request("POST", "/auth/logout")
            except Exception:
                pass
            st.session_state["auth"] = {"token": None, "username": None, "role": None}
            st.session_state["recognized_history"] = []
            st.session_state["route_results"] = None
            st.experimental_rerun()
        st.sidebar.markdown("---")
        return

    login_expander = st.sidebar.expander("🔑 Вход", expanded=True)
    with login_expander:
        with st.form("login_form"):
            login_username = st.text_input("Имя пользователя", key="login_username")
            login_password = st.text_input("Пароль", type="password", key="login_password")
            if st.form_submit_button("Войти"):
                if not login_username or not login_password:
                    st.warning("Введите имя пользователя и пароль.")
                else:
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/auth/login",
                            json={"username": login_username, "password": login_password},
                        )
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state["auth"] = {
                                "token": data["token"],
                                "username": data["username"],
                                "role": data["role"],
                            }
                            refresh_recognition_history()
                            st.success("Вы успешно вошли в систему.")
                            st.experimental_rerun()
                        else:
                            st.error(response.json().get("detail", "Не удалось войти."))
                    except Exception as exc:
                        st.error(f"Ошибка при входе: {exc}")

    register_expander = st.sidebar.expander("🆕 Регистрация", expanded=False)
    with register_expander:
        with st.form("register_form"):
            reg_username = st.text_input("Имя пользователя", key="register_username")
            reg_password = st.text_input("Пароль", type="password", key="register_password")
            role_map = {"Путешественник": "user", "Администратор": "admin"}
            reg_role_label = st.selectbox("Тип аккаунта", list(role_map.keys()))
            if st.form_submit_button("Зарегистрироваться"):
                if not reg_username or not reg_password:
                    st.warning("Заполните имя пользователя и пароль.")
                else:
                    try:
                        payload = {
                            "username": reg_username,
                            "password": reg_password,
                            "role": role_map[reg_role_label],
                        }
                        response = requests.post(f"{API_BASE_URL}/auth/register", json=payload)
                        if response.status_code == 200:
                            st.success("Регистрация прошла успешно. Теперь войдите в систему.")
                        else:
                            st.error(response.json().get("detail", "Не удалось зарегистрировать пользователя."))
                    except Exception as exc:
                        st.error(f"Ошибка при регистрации: {exc}")


def refresh_recognition_history() -> None:
    if not is_authenticated():
        st.session_state["recognized_history"] = []
        return
    try:
        response = auth_api_request("GET", "/auth/me/recognized")
        if response.status_code == 200:
            st.session_state["recognized_history"] = response.json()
        else:
            st.session_state["recognized_history"] = []
    except Exception:
        st.session_state["recognized_history"] = []


# ---------------------------------------------------------------------------
# Visitor interface
# ---------------------------------------------------------------------------
def visitor_interface() -> None:
    st.title("🏠 Интерфейс посетителя")
    st.markdown(
        "Загрузите фотографию достопримечательности, спланируйте маршрут путешествия "
        "и просмотрите историю распознаваний."
    )
    render_recognition_section()
    render_route_planner()
    render_history_section()
    render_example_objects()


def render_recognition_section() -> None:
    st.subheader("🔍 Распознавание достопримечательности")
    uploaded_file = st.file_uploader(
        "Выберите изображение (JPG/PNG, до 10MB)",
        type=["jpg", "jpeg", "png"],
    )

    if uploaded_file:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Загруженное изображение", use_column_width=True)
        
        with col2:
            st.markdown("**Результат**")
            if st.button("Распознать", type="primary"):
                with st.spinner("Анализируем изображение..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        response = auth_api_request("POST", "/api/recognize", files=files)
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("success"):
                                st.success(result.get("message", "Объект распознан."))
                                st.markdown(f"**ID объекта:** {result.get('object_id')}")
                                st.markdown(f"**Уверенность:** {result.get('confidence', 0):.2%}")
                                if result.get("distance") is not None:
                                    st.markdown(f"**Дистанция векторного поиска:** {result['distance']}")
                                st.markdown("**Описание:**")
                                st.markdown(result.get("description") or "_Описание недоступно._")
                                if result.get("history_entry"):
                                    refresh_recognition_history()
                            else:
                                st.warning(result.get("message", "Объект не распознан."))
                        else:
                            st.error(f"Ошибка API: {response.status_code}")
                            st.code(response.text)
                    except Exception as exc:
                        st.error(f"Ошибка при распознавании: {exc}")


def render_history_section() -> None:
    st.subheader("📜 История распознаваний")
    if not is_authenticated():
        st.info("Войдите в систему, чтобы смотреть и сохранять историю распознаваний.")
        return

    if st.button("Обновить историю", key="refresh_history_button"):
        refresh_recognition_history()

    history = st.session_state.get("recognized_history", [])
    if not history:
        st.info("Пока нет записей в истории распознаваний.")
        return

    for record in history:
        created_at = datetime.fromisoformat(record["created_at"]).strftime("%d.%m.%Y %H:%M")
        header = (
            f"ID {record['object_id']} • уверенность {record['confidence']:.2%} • {created_at}"
        )
        with st.expander(header):
            if record.get("image_url"):
                image_url = f"{API_BASE_URL}{record['image_url']}"
                st.image(image_url, use_column_width=True, caption="Сохранённое изображение")
            st.markdown(record.get("description") or "_Описание недоступно._")
            st.caption(f"Дистанция: {record['distance']:.4f}")


def render_route_planner() -> None:
    st.subheader("🧭 Спланировать маршрут перед путешествием")
    with st.form("route_form"):
        col1, col2, col3 = st.columns([1, 1, 1])
        latitude = col1.number_input("Широта (например, 43.0000)", value=43.000000, format="%.6f")
        longitude = col2.number_input("Долгота (например, 44.0000)", value=44.000000, format="%.6f")
        limit = col3.slider("Количество точек", min_value=3, max_value=15, value=10)
        submitted = st.form_submit_button("Спланировать маршрут", type="primary")
        
        if submitted:
            with st.spinner("Ищем ближайшие достопримечательности..."):
                try:
                    payload = {"latitude": latitude, "longitude": longitude, "limit": limit}
                    response = requests.post(f"{API_BASE_URL}/api/plan-route", json=payload)
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("success"):
                            st.session_state["route_results"] = result
                        else:
                            st.warning(result.get("message", "Не удалось построить маршрут."))
                            st.session_state["route_results"] = None
                    else:
                        st.error(f"Ошибка API: {response.status_code}")
                        st.session_state["route_results"] = None
                except Exception as exc:
                    st.error(f"Ошибка при построении маршрута: {exc}")
                    st.session_state["route_results"] = None

    route = st.session_state.get("route_results")
    if not route:
        return

    st.markdown(
        f"**Стартовая точка:** {route['start']['latitude']:.4f}, {route['start']['longitude']:.4f}  \n"
        f"**Суммарная протяжённость:** {route['total_distance_km']:.2f} км"
    )
    render_attraction_cards(route["points"], columns=3, show_distances=True)


def render_example_objects() -> None:
    st.subheader("📚 Примеры достопримечательностей")
    try:
        response = requests.get(f"{API_BASE_URL}/api/objects")
        if response.status_code == 200:
            data = response.json()
            objects = data.get("objects", []) if data.get("success") else []
            if objects:
                render_attraction_cards(objects[:6], columns=3, show_distances=False)
            else:
                st.info("В базе пока нет объектов.")
        else:
            st.error(f"Ошибка API: {response.status_code}")
    except Exception as exc:
        st.error(f"Ошибка при загрузке примеров: {exc}")


def render_attraction_cards(
    attractions: List[Dict[str, Any]], columns: int = 3, show_distances: bool = False
) -> None:
    if not attractions:
        st.info("Нет данных для отображения.")
        return

    for idx, attraction in enumerate(attractions):
        if idx % columns == 0:
            cols = st.columns(columns)
        column = cols[idx % columns]
        with column:
            column.markdown(f"### {attraction.get('name', 'Неизвестный объект')}")
            if show_distances:
                column.caption(
                    f"От предыдущей точки: {attraction.get('distance_from_previous_km', 0):.2f} км  \n"
                    f"Суммарно: {attraction.get('cumulative_distance_km', 0):.2f} км"
                )
            else:
                column.caption(attraction.get("location", "Локация неизвестна"))

            images = attraction.get("example_images") or []
            if images:
                image_path = images[0]
                full_url = f"{API_BASE_URL}/dataset/{image_path}"
                try:
                    column.image(full_url, use_column_width=True)
                except Exception:
                    local_path = os.path.join("dataset", image_path)
                    if os.path.exists(local_path):
                        column.image(local_path, use_column_width=True)
            column.markdown(attraction.get("description", "_Описание отсутствует._"))


# ---------------------------------------------------------------------------
# Admin interface
# ---------------------------------------------------------------------------
def admin_interface() -> None:
    st.title("⚙️ Админ панель")
    st.markdown("Управление достопримечательностями и контентом.")

    if not is_authenticated():
        st.info("Для доступа к админ-панели войдите в систему.")
        return
    if not is_admin():
        st.warning("Для доступа необходим аккаунт администратора.")
        return

    st.subheader("➕ Добавить новый объект")
    with st.form("add_object_form"):
        object_name = st.text_input("Название достопримечательности", key="new_object_name")
        object_location = st.text_input(
            "Местоположение (координаты и описание)", key="new_object_location"
        )
        object_description = st.text_area(
            "Описание достопримечательности",
            height=200,
            key="new_object_description",
        )
        object_images = st.file_uploader(
            "Изображения объекта",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="new_object_images",
        )
        submitted = st.form_submit_button("Добавить", type="primary")

    if submitted:
        if not object_name or not object_description or not object_images:
            st.error("Заполните все поля и загрузите хотя бы одно изображение.")
        else:
            files = []
            for i, img in enumerate(object_images):
                files.append(("images", (img.name or f"image_{i}.jpg", img.getvalue(), img.type)))
            data = {"name": object_name, "description": object_description, "location": object_location}
            try:
                response = auth_api_request("POST", "/api/objects", data=data, files=files)
                if response.status_code == 200 and response.json().get("success"):
                    st.success("Объект добавлен.")
                    st.experimental_rerun()
                else:
                    st.error(response.json().get("detail", "Не удалось добавить объект."))
            except Exception as exc:
                st.error(f"Ошибка при добавлении: {exc}")

    st.subheader("✏️ Редактировать существующие объекты")
    try:
        response = requests.get(f"{API_BASE_URL}/api/objects")
        if response.status_code == 200:
            data = response.json()
            objects = data.get("objects", []) if data.get("success") else []
            if not objects:
                st.info("В базе пока нет объектов.")
            for obj in objects:
                with st.expander(f"{obj['id']}: {obj['name']}"):
                    with st.form(f"edit_object_{obj['id']}"):
                        new_name = st.text_input("Название", value=obj["name"], key=f"name_{obj['id']}")
                        new_location = st.text_input(
                            "Местоположение", value=obj.get("location", ""), key=f"loc_{obj['id']}"
                        )
                        new_description = st.text_area(
                            "Описание", value=obj["description"], height=200, key=f"desc_{obj['id']}"
                        )
                        if st.form_submit_button("Сохранить изменения"):
                            data = {
                                "name": new_name,
                                "location": new_location,
                                "description": new_description,
                            }
                            try:
                                response = auth_api_request(
                                    "PUT",
                                    f"/api/objects/{obj['id']}",
                                    data=data,
                                )
                                if response.status_code == 200 and response.json().get("success"):
                                    st.success("Объект обновлён.")
                                    st.experimental_rerun()
                                else:
                                    st.error(response.json().get("detail", "Не удалось обновить объект."))
                            except Exception as exc:
                                st.error(f"Ошибка при обновлении: {exc}")
        else:
            st.error(f"Ошибка API: {response.status_code}")
    except Exception as exc:
        st.error(f"Ошибка при загрузке объектов: {exc}")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------
def system_stats() -> None:
    st.title("📊 Статистика системы")
    st.markdown("Общая информация о состоянии платформы.")

    try:
        response = requests.get(f"{API_BASE_URL}/api/stats")
        if response.status_code != 200:
            st.error(f"Ошибка API: {response.status_code}")
            return

        data = response.json()
        if not data.get("success"):
            st.error("Не удалось получить статистику.")
            return

        stats = data["stats"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Объекты", stats.get("total_objects", 0))
        col2.metric("Изображения", stats.get("total_images", 0))
        col3.metric("Распознавания", stats.get("recognized_records", 0))
        col4.metric("Пользователи", stats.get("total_users", 0))

        status_color = "🟢" if stats.get("system_status") == "operational" else "🔴"
        st.info(
            f"{status_color} Статус: {stats.get('system_status')}  \n"
            f"Последнее обновление: {stats.get('last_updated', '')}"
        )

        health_response = requests.get(f"{API_BASE_URL}/health")
        if health_response.status_code == 200:
            health = health_response.json()
            st.success(
                f"RAG Searcher: {health.get('rag_searcher')} — {health.get('timestamp')}"
            )
        else:
            st.warning("Не удалось получить статус здоровья сервиса.")

    except Exception as exc:
        st.error(f"Ошибка при получении статистики: {exc}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Распознавание достопримечательностей Северного Кавказа",
        page_icon="🏔️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    handle_auth_sidebar()

    page = st.sidebar.selectbox(
        "Выберите раздел",
        ["🏠 Интерфейс посетителя", "⚙️ Админ панель", "📊 Статистика системы"],
    )

    if page == "🏠 Интерфейс посетителя":
        visitor_interface()
    elif page == "⚙️ Админ панель":
        admin_interface()
    else:
        system_stats()


if __name__ == "__main__":
    main()
