"""
FastAPI application for North Caucasus Tourist Attractions Recognition System.

This module provides a REST API for recognizing tourist attractions in North Caucasus,
managing user accounts, storing recognition history, and planning travel routes.

Факультет Искусственного Интеллекта РУДН
"""

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Form,
    Depends,
    Header,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import json
import shutil
import hashlib
import uuid
import re
import math
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    ForeignKey,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.exc import IntegrityError

from pydantic import BaseModel, Field

from rag_searcher import RAGSearcher

# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------
DATABASE_URL = "sqlite:///users.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    token = Column(String(64), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    recognized_images = relationship(
        "RecognizedImage", back_populates="user", cascade="all, delete-orphan"
    )


class RecognizedImage(Base):
    __tablename__ = "recognized_images"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    object_id = Column(Integer, nullable=False)
    distance = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    image_path = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="recognized_images")


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    username: str
    password: str
    role: str = Field("user", description="user или admin")


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    success: bool
    token: str
    username: str
    role: str


class RecognizedImageOut(BaseModel):
    id: int
    object_id: int
    distance: float
    confidence: float
    description: Optional[str]
    image_url: Optional[str]
    created_at: datetime


class RouteRequest(BaseModel):
    latitude: float
    longitude: float
    limit: int = Field(10, ge=1, le=30)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_token() -> str:
    return uuid.uuid4().hex


def extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return authorization.strip()


def get_user_by_token(db: Session, token: Optional[str]) -> Optional[User]:
    if not token:
        return None
    return db.query(User).filter(User.token == token).first()


def require_authenticated_user(
    db: Session, authorization: Optional[str]
) -> User:
    token = extract_token(authorization)
    user = get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    return user


def require_admin(db: Session, authorization: Optional[str]) -> User:
    user = require_authenticated_user(db, authorization)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Недостаточно прав для операции")
    return user


def collect_example_images(obj_id: int, limit: int = 3) -> List[str]:
    images: List[str] = []
    dataset_root = "dataset"
    folder_prefix = f"{obj_id:02d}_"

    if not os.path.exists(dataset_root):
        return images

    target_folder = None
    for folder in os.listdir(dataset_root):
        folder_path = os.path.join(dataset_root, folder)
        if os.path.isdir(folder_path) and folder.startswith(folder_prefix):
            target_folder = folder
            break

    if not target_folder:
        return images

    folder_path = os.path.join(dataset_root, target_folder)

    def append_images(directory: str, max_items: int) -> None:
        if not os.path.exists(directory):
            return
        for file in sorted(os.listdir(directory)):
            if len(images) >= max_items:
                break
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path) and file.lower().endswith((".jpg", ".jpeg")):
                relative = os.path.relpath(file_path, dataset_root).replace("\\", "/")
                images.append(relative)

    append_images(folder_path, limit)
    ground_path = os.path.join(folder_path, "ground")
    append_images(ground_path, limit)

    return images[:limit]


def compose_description(obj: Dict[str, Any]) -> str:
    description = f"Название: {obj.get('Название', '')}\n"
    description += f"Местоположение: {obj.get('Местоположение', '')}\n"
    description += "\nКраткая историческая справка:\n"
    description += obj.get("Краткая историческая справка", "")
    return description


def parse_dms_component(value: str) -> Optional[float]:
    match = re.match(
        r"^\s*(?P<deg>-?\d+)[°º]?\s*(?P<min>\d+)?[′'’]?\s*(?P<sec>\d+)?[\"″]?\s*(?P<dir>[NSEW])\s*$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    deg = int(match.group("deg"))
    minutes = int(match.group("min") or 0)
    seconds = int(match.group("sec") or 0)
    result = abs(deg) + minutes / 60.0 + seconds / 3600.0
    direction = match.group("dir").upper()
    if direction in {"S", "W"}:
        result = -result
    return result


def parse_coordinates(raw_location: str) -> Optional[Tuple[float, float]]:
    if not raw_location:
        return None

    decimal_matches = re.findall(r"[-+]?\d+\.\d+", raw_location.replace(",", "."))
    if len(decimal_matches) >= 2:
        try:
            lat = float(decimal_matches[0])
            lon = float(decimal_matches[1])
            return lat, lon
        except ValueError:
            pass

    # Attempt to capture DMS patterns
    dms_matches = re.findall(
        r"(\d+[°º]\s*\d*[′'’]?\s*\d*[\"″]?\s*[NSEW])", raw_location, flags=re.IGNORECASE
    )
    if len(dms_matches) >= 2:
        lat = parse_dms_component(dms_matches[0])
        lon = parse_dms_component(dms_matches[1])
        if lat is not None and lon is not None:
            return lat, lon

    return None


def load_object_entries() -> List[Dict[str, Any]]:
    if not os.path.exists("artifacts_turism/turism.json"):
        return []

    with open("artifacts_turism/turism.json", "r", encoding="utf-8") as f:
        objects: List[Dict[str, Any]] = json.load(f)

    entries: List[Dict[str, Any]] = []
    for obj in objects:
        obj_id = obj.get("id")
        location = obj.get("Местоположение", "")
        coordinates = parse_coordinates(location)
        example_images = collect_example_images(obj_id)

        entry = {
            "id": obj_id,
            "name": obj.get("Название", f"Достопримечательность {obj_id}"),
            "description": compose_description(obj),
            "location": location,
            "image_count": len(example_images),
            "example_images": example_images,
            "coordinates": {
                "latitude": coordinates[0],
                "longitude": coordinates[1],
            }
            if coordinates
            else None,
            "raw": obj,
        }
        entries.append(entry)
    return entries


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def build_route(
    start_lat: float, start_lon: float, candidates: List[Dict[str, Any]], limit: int
) -> Tuple[List[Dict[str, Any]], float]:
    with_coordinates = [
        c for c in candidates if c.get("coordinates") is not None
    ]
    if not with_coordinates:
        return [], 0.0

    # Greedy nearest neighbor path
    remaining = with_coordinates.copy()
    route: List[Dict[str, Any]] = []
    current_lat = start_lat
    current_lon = start_lon
    cumulative_distance = 0.0

    for _ in range(min(limit, len(remaining))):
        nearest = min(
            remaining,
            key=lambda c: haversine_km(
                current_lat,
                current_lon,
                c["coordinates"]["latitude"],
                c["coordinates"]["longitude"],
            ),
        )
        distance = haversine_km(
            current_lat,
            current_lon,
            nearest["coordinates"]["latitude"],
            nearest["coordinates"]["longitude"],
        )
        cumulative_distance += distance
        route.append(
            {
                "id": nearest["id"],
                "name": nearest["name"],
                "location": nearest["location"],
                "description": nearest["description"],
                "example_images": nearest["example_images"],
                "coordinates": nearest["coordinates"],
                "distance_from_previous_km": round(distance, 3),
                "cumulative_distance_km": round(cumulative_distance, 3),
            }
        )
        current_lat = nearest["coordinates"]["latitude"]
        current_lon = nearest["coordinates"]["longitude"]
        remaining.remove(nearest)

    return route, cumulative_distance


def ensure_directories() -> None:
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("uploads/users", exist_ok=True)
    os.makedirs("pool/recognized", exist_ok=True)


def store_recognition_for_user(
    db: Session,
    user: User,
    object_id: int,
    distance: float,
    confidence: float,
    description: Optional[str],
    temp_path: str,
) -> RecognizedImage:
    user_dir = os.path.join("uploads", "users", f"user_{user.id}")
    os.makedirs(user_dir, exist_ok=True)

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_obj_{object_id:02d}.jpg"
    destination = os.path.join(user_dir, filename)
    shutil.copy2(temp_path, destination)

    relative_path = os.path.relpath(destination, "uploads").replace("\\", "/")

    record = RecognizedImage(
        user_id=user.id,
        object_id=object_id,
        distance=distance,
        confidence=confidence,
        description=description,
        image_path=relative_path,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# FastAPI application and configuration
# ---------------------------------------------------------------------------
app = FastAPI(
    title="API распознавания туристических достопримечательностей Северного Кавказа",
    description=(
        "ИИ-система для идентификации достопримечательностей Северного Кавказа, "
        "управления пользователями и планирования маршрутов. "
        "Факультет Искусственного Интеллекта РУДН."
    ),
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG searcher
try:
    ragger: Optional[RAGSearcher] = RAGSearcher(
        device="cpu",
        vectorstore_path="artifacts/db",
        object_descr_path="artifacts_turism/turism.json",
        similarity_threshold=0.90,
    )
    print("✅ RAG searcher initialized successfully")
except Exception as e:
    print(f"❌ Error initializing RAG searcher: {e}")
    ragger = None

# Prepare filesystem
ensure_directories()
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/dataset", StaticFiles(directory="dataset"), name="dataset")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "message": "API распознавания туристических достопримечательностей Северного Кавказа",
        "version": "1.1.0",
        "status": "running",
        "organization": "Факультет Искусственного Интеллекта РУДН",
        "endpoints": {
            "recognize": "POST /api/recognize",
            "objects": "GET /api/objects",
            "plan_route": "POST /api/plan-route",
            "stats": "GET /api/stats",
            "register": "POST /auth/register",
            "login": "POST /auth/login",
            "me": "GET /auth/me",
        },
    }


@app.post("/auth/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    username = user.username.strip()
    role = user.role.lower().strip()

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Имя пользователя должно содержать минимум 3 символа")
    if len(user.password) < 6:
        raise HTTPException(status_code=400, detail="Пароль должен содержать минимум 6 символов")
    if role not in {"user", "admin"}:
        raise HTTPException(status_code=400, detail="Некорректная роль. Допустимо: user или admin")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")

    db_user = User(username=username, password_hash=hash_password(user.password), role=role)
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Не удалось создать пользователя")
    db.refresh(db_user)

    return {
        "success": True,
        "message": "Пользователь успешно зарегистрирован",
        "username": db_user.username,
        "role": db_user.role,
    }


@app.post("/auth/login", response_model=TokenResponse)
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username.strip()).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    db_user.token = create_token()
    db.commit()
    return TokenResponse(
        success=True,
        token=db_user.token,
        username=db_user.username,
        role=db_user.role,
    )


@app.post("/auth/logout")
def logout_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    user = require_authenticated_user(db, authorization)
    user.token = None
    db.commit()
    return {"success": True, "message": "Вы успешно вышли из системы"}


@app.get("/auth/me")
def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
) -> Dict[str, Any]:
    user = require_authenticated_user(db, authorization)
    return {
        "success": True,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
    }


@app.get("/auth/me/recognized", response_model=List[RecognizedImageOut])
def get_recognition_history(
    limit: int = 50,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    user = require_authenticated_user(db, authorization)
    records = (
        db.query(RecognizedImage)
        .filter(RecognizedImage.user_id == user.id)
        .order_by(RecognizedImage.created_at.desc())
        .limit(limit)
        .all()
    )

    response: List[RecognizedImageOut] = []
    for record in records:
        image_url = None
        if record.image_path:
            image_url = f"/uploads/{record.image_path}"
        response.append(
            RecognizedImageOut(
                id=record.id,
                object_id=record.object_id,
                distance=record.distance,
                confidence=record.confidence,
                description=record.description,
                image_url=image_url,
                created_at=record.created_at,
            )
        )
    return response


@app.post("/api/recognize")
async def recognize_object(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    if not ragger:
        raise HTTPException(status_code=500, detail="RAG searcher not initialized")
    
    if not file:
        raise HTTPException(status_code=400, detail="Файл не загружен")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой. Максимальный размер 10MB")
    
    temp_path: Optional[str] = None
    user: Optional[User] = None
    token = extract_token(authorization)
    if token:
        user = get_user_by_token(db, token)

    try:
        temp_path = f"uploads/temp_{uuid.uuid4()}.jpg"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            raise HTTPException(status_code=400, detail="Не удалось сохранить загруженный файл")
        
        result = ragger.search(temp_path)
        
        if result is None:
            return {
                "success": False,
                "message": (
                    "Похоже, вы загрузили изображение не из базы туристических достопримечательностей "
                    "Северного Кавказа. Пожалуйста, попробуйте другой ракурс или другое изображение."
                ),
                "confidence": 0.0,
                "object_id": None,
                "description": None,
                "distance": None,
            }

        object_id, distance = result
        distance = float(distance)
        confidence = max(0.0, 1.0 - (distance / 0.9))

        description = None
        try:
            description = ragger.get_description(object_id)
        except Exception as e:
            print(f"Error getting description for object {object_id}: {e}")

        saved_pool_path = None
        if distance < 0.5:
            try:
                saved_pool_path = (
                    f"pool/recognized/obj_{object_id:02d}_dist_{distance:.4f}_"
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                )
                shutil.copy2(temp_path, saved_pool_path)
                print(f"✅ Saved well-recognized image to pool: {saved_pool_path} (distance: {distance:.4f})")
            except Exception as pool_error:
                print(f"⚠️ Could not save to pool: {pool_error}")

        history_entry = None
        if user and description:
            record = store_recognition_for_user(
                db=db,
                user=user,
                object_id=int(object_id),
                distance=distance,
                confidence=confidence,
                description=description,
                temp_path=temp_path,
            )
            history_entry = {
                "id": record.id,
                "object_id": record.object_id,
                "distance": record.distance,
                "confidence": record.confidence,
                "description": record.description,
                "image_url": f"/uploads/{record.image_path}",
                "created_at": record.created_at.isoformat(),
            }

        response = {
            "success": True,
            "message": "Туристическая достопримечательность успешно распознана",
            "confidence": round(confidence, 3),
            "object_id": int(object_id),
            "description": description,
            "distance": round(distance, 4),
        }
        if history_entry:
            response["history_entry"] = history_entry
        if saved_pool_path:
            response["saved_pool_image"] = saved_pool_path
        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"Recognition error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Распознавание не удалось: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up temp file {temp_path}: {cleanup_error}")


@app.get("/api/objects")
async def get_objects() -> Dict[str, Any]:
    try:
        entries = load_object_entries()
        formatted = []
        for entry in entries:
            payload = {
                "id": entry["id"],
                "name": entry["name"],
                "description": entry["description"],
                "location": entry["location"],
                "image_count": entry["image_count"],
                "example_images": entry["example_images"],
            }
            if entry["coordinates"]:
                payload["coordinates"] = entry["coordinates"]
            formatted.append(payload)
        return {"success": True, "objects": formatted}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Файл с объектами не найден")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Ошибка чтения файла с объектами")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить объекты: {str(e)}")


@app.post("/api/objects")
async def add_object(
    name: str = Form(...),
    description: str = Form(...),
    location: str = Form(""),
    images: List[UploadFile] = File(...),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    require_admin(db, authorization)

    try:
        objects = []
        if os.path.exists("artifacts_turism/turism.json"):
            with open("artifacts_turism/turism.json", "r", encoding="utf-8") as f:
                objects = json.load(f)

        new_id = max([obj.get("id", 0) for obj in objects]) + 1 if objects else 1

        safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip()) or f"object_{new_id}"
        dataset_folder = os.path.join("dataset", f"{new_id:02d}_{safe_name}")
        os.makedirs(dataset_folder, exist_ok=True)

        image_paths: List[str] = []
        for i, image in enumerate(images, start=1):
            if not image.content_type or not image.content_type.startswith("image/"):
                continue
            ext = os.path.splitext(image.filename or "")[1].lower()
            if ext not in {".jpg", ".jpeg", ".png"}:
                ext = ".jpg"
            filename = f"photo_{i}{ext}"
            destination = os.path.join(dataset_folder, filename)
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_paths.append(destination)

        new_object = {
            "id": new_id,
            "Название": name,
            "Местоположение": location,
            "Краткая историческая справка": description,
            "created_at": datetime.now().isoformat(),
        }
        objects.append(new_object)

        with open("artifacts_turism/turism.json", "w", encoding="utf-8") as f:
            json.dump(objects, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": "Объект успешно добавлен",
            "object": new_object,
            "images_saved": len(image_paths),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось добавить объект: {str(e)}")


@app.put("/api/objects/{object_id}")
async def edit_object(
    object_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    require_admin(db, authorization)

    try:
        if not os.path.exists("artifacts_turism/turism.json"):
            raise HTTPException(status_code=404, detail="База объектов не найдена")

        with open("artifacts_turism/turism.json", "r", encoding="utf-8") as f:
            objects = json.load(f)

        obj_index = None
        for idx, obj in enumerate(objects):
            if obj.get("id") == object_id:
                obj_index = idx
                break

        if obj_index is None:
            raise HTTPException(status_code=404, detail="Объект не найден")
        
        if name:
            objects[obj_index]["Название"] = name
        if description:
            objects[obj_index]["Краткая историческая справка"] = description
        if location is not None:
            objects[obj_index]["Местоположение"] = location
        objects[obj_index]["updated_at"] = datetime.now().isoformat()
        
        with open("artifacts_turism/turism.json", "w", encoding="utf-8") as f:
            json.dump(objects, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "message": "Объект успешно обновлен",
            "object_id": object_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось обновить объект: {str(e)}")


@app.post("/api/plan-route")
async def plan_route(request: RouteRequest) -> Dict[str, Any]:
    try:
        entries = load_object_entries()
        route, total_distance = build_route(
            start_lat=request.latitude,
            start_lon=request.longitude,
            candidates=entries,
            limit=request.limit,
        )

        if not route:
            return {
                "success": False,
                "message": "Не удалось построить маршрут: нет объектов с координатами",
                "route": [],
            }

        return {
            "success": True,
            "start": {
                "latitude": request.latitude,
                "longitude": request.longitude,
            },
            "total_distance_km": round(total_distance, 3),
            "points": route,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось построить маршрут: {str(e)}")


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        entries = load_object_entries()
        total_images = 0
        if os.path.exists("dataset"):
            for folder in sorted(os.listdir("dataset")):
                folder_path = os.path.join("dataset", folder)
                if os.path.isdir(folder_path):
                    for file in os.listdir(folder_path):
                        file_path = os.path.join(folder_path, file)
                        if os.path.isfile(file_path) and file.lower().endswith((".jpg", ".jpeg")):
                            total_images += 1
                    ground_path = os.path.join(folder_path, "ground")
                    if os.path.exists(ground_path) and os.path.isdir(ground_path):
                        for file in os.listdir(ground_path):
                            if file.lower().endswith((".jpg", ".jpeg")):
                                total_images += 1

        user_count = db.query(User).count()
        recognized_count = db.query(RecognizedImage).count()
        
        return {
            "success": True,
            "stats": {
                "total_objects": len(entries),
                "total_images": total_images,
                "recognized_records": recognized_count,
                "total_users": user_count,
                "system_status": "operational" if ragger else "error",
                "last_updated": datetime.now().isoformat(),
                "organization": "Факультет Искусственного Интеллекта РУДН",
                "database": "turism.json",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Не удалось получить статистику: {str(e)}")


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "status": "healthy",
        "rag_searcher": "initialized" if ragger else "error",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
