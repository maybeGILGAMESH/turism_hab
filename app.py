from __future__ import annotations

import csv
import hashlib
import math
import mimetypes
import secrets
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, create_engine, select
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)

from build_index import build as build_faiss_index
from catalog import Attraction, load_catalog, save_catalog
from data_pipeline import Manifest, assign_splits
from rag_searcher import IndexNotReady, RAGSearcher
from settings import ROOT, Settings, get_settings

settings: Settings = get_settings()
for folder in (
    ROOT / "runtime",
    ROOT / "uploads",
    ROOT / "dataset" / "processed",
    ROOT / "artifacts",
):
    folder.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    recognitions: Mapped[list[Recognition]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class SessionToken(Base):
    __tablename__ = "session_tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Recognition(Base):
    __tablename__ = "recognitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    object_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(default=0.0)
    image_url: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    user: Mapped[User] = relationship(back_populates="recognitions")


database_url = settings.database_url
if database_url.startswith("sqlite:///runtime/"):
    database_url = f"sqlite:///{(ROOT / database_url.removeprefix('sqlite:///')).as_posix()}"
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base.metadata.create_all(engine)
password_hasher = PasswordHasher()


def bootstrap_admin() -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == settings.admin_email.lower()))
        if existing is None:
            db.add(
                User(
                    email=settings.admin_email.lower(),
                    password_hash=password_hasher.hash(settings.admin_password),
                    is_admin=True,
                )
            )
            db.commit()


bootstrap_admin()
searcher = RAGSearcher(settings)
index_state: dict[str, object] = {"running": False, "error": "", "finished_at": None}
index_lock = Lock()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Распознавание и каталог достопримечательностей Хабаровского края",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.mount("/dataset", StaticFiles(directory=ROOT / "dataset" / "processed"), name="dataset")
app.mount("/uploads", StaticFiles(directory=ROOT / "uploads"), name="uploads")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RouteRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    limit: int = Field(default=10, ge=1, le=20)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def token_hash(token: str) -> str:
    return hashlib.sha256(f"{settings.app_secret}:{token}".encode()).hexdigest()


def bearer_token(authorization: str | None) -> str | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization.split(" ", 1)[1].strip()


def current_user(db: Session, authorization: str | None) -> User | None:
    token = bearer_token(authorization)
    if not token:
        return None
    row = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash(token)))
    if row is None:
        return None
    expiry = row.expires_at.replace(tzinfo=UTC) if row.expires_at.tzinfo is None else row.expires_at
    if expiry <= datetime.now(UTC):
        db.delete(row)
        db.commit()
        return None
    return db.get(User, row.user_id)


def require_user(
    authorization: Annotated[str | None, Header()] = None, db: Session = Depends(get_db)
) -> User:
    user = current_user(db, authorization)
    if user is None:
        raise HTTPException(401, "Требуется авторизация")
    return user


def require_admin(
    authorization: Annotated[str | None, Header()] = None, db: Session = Depends(get_db)
) -> User:
    user = current_user(db, authorization)
    if user is None or not user.is_admin:
        raise HTTPException(403, "Требуются права администратора")
    return user


def catalog_map() -> dict[int, Attraction]:
    return {
        item.id: item
        for item in load_catalog(settings.absolute(settings.catalog_path))
        if item.enabled
    }


def examples_by_object() -> dict[int, list[str]]:
    manifest_path = settings.absolute(settings.manifest_path)
    result: dict[int, list[str]] = {}
    if not manifest_path.exists():
        return result
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") != "accepted" or not row.get("processed_path"):
                continue
            object_id = int(row["object_id"])
            if object_id <= 0 or len(result.setdefault(object_id, [])) >= 3:
                continue
            relative = Path(row["processed_path"])
            try:
                image_relative = relative.relative_to("dataset/processed")
            except ValueError:
                continue
            result[object_id].append(f"/dataset/{image_relative.as_posix()}")
    return result


def public_object(
    item: Attraction, examples: dict[int, list[str]] | None = None
) -> dict[str, object]:
    payload = item.model_dump(exclude={"search_queries"})
    ready_ids = {int(value) for value in searcher.metadata.get("ready_object_ids", [])}
    payload["index_status"] = (
        "ready" if searcher.ready and item.id in ready_ids else "pending_index"
    )
    payload["coordinates"] = (
        {"latitude": item.latitude, "longitude": item.longitude}
        if item.latitude is not None and item.longitude is not None
        else None
    )
    payload["example_images"] = (examples or {}).get(item.id, [])
    payload["image_count"] = len(payload["example_images"])
    return payload


def haversine(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    radius = 6371.0
    dlat, dlon = math.radians(b_lat - a_lat), math.radians(b_lon - a_lon)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(a_lat)) * math.cos(math.radians(b_lat)) * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(ROOT / "static" / "index.html")


@app.post("/auth/register")
def register(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Пользователь уже существует")
    user = User(email=email, password_hash=password_hasher.hash(payload.password), is_admin=False)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"success": True, "user": {"id": user.id, "email": user.email, "role": "user"}}


@app.post("/auth/login")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None:
        raise HTTPException(401, "Неверные учётные данные")
    try:
        password_hasher.verify(user.password_hash, payload.password)
    except VerifyMismatchError as error:
        raise HTTPException(401, "Неверные учётные данные") from error
    raw = secrets.token_urlsafe(32)
    db.add(
        SessionToken(
            token_hash=token_hash(raw),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    db.commit()
    return {
        "access_token": raw,
        "token_type": "bearer",
        "expires_in": 604800,
        "role": "admin" if user.is_admin else "user",
    }


@app.post("/auth/logout")
def logout(authorization: Annotated[str | None, Header()] = None, db: Session = Depends(get_db)):
    token = bearer_token(authorization)
    if token:
        row = db.scalar(select(SessionToken).where(SessionToken.token_hash == token_hash(token)))
        if row:
            db.delete(row)
            db.commit()
    return {"success": True}


@app.get("/auth/me")
def me(user: User = Depends(require_user)):
    return {"id": user.id, "email": user.email, "role": "admin" if user.is_admin else "user"}


@app.get("/auth/me/recognized")
def history(user: User = Depends(require_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Recognition)
        .where(Recognition.user_id == user.id)
        .order_by(Recognition.created_at.desc())
    ).all()
    return [
        {
            "id": row.id,
            "object_id": row.object_id,
            "object_name": row.object_name,
            "confidence": row.confidence,
            "image_url": row.image_url,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@app.get("/api/objects")
def get_objects():
    examples = examples_by_object()
    return {
        "success": True,
        "objects": [public_object(item, examples) for item in catalog_map().values()],
    }


@app.post("/api/recognize")
async def recognize(
    file: UploadFile = File(...),
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Поддерживаются JPEG, PNG и WebP")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Максимальный размер файла — {settings.max_upload_mb} МБ")
    suffix = mimetypes.guess_extension(file.content_type) or ".jpg"
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, dir=ROOT / "runtime"
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        with Image.open(temp_path) as probe:
            probe.verify()
        result = searcher.search(temp_path)
    except UnidentifiedImageError as error:
        raise HTTPException(400, "Файл не является корректным изображением") from error
    except IndexNotReady as error:
        raise HTTPException(503, f"Индекс не готов: {error}") from error
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    attraction = result.pop("object")
    payload = {
        "success": bool(result["recognized"]),
        "recognized": bool(result["recognized"]),
        "object_id": attraction.id if attraction else None,
        "confidence": max(0.0, min(1.0, float(result["score"]))) if attraction else 0.0,
        "description": attraction.description if attraction else "Объект не распознан уверенно.",
        "object": public_object(attraction) if attraction else None,
        "top_matches": result["candidates"],
        "score": result["score"],
        "margin": result["margin"],
        "model_version": result["model_version"],
        "dataset_version": result["dataset_version"],
    }
    user = current_user(db, authorization)
    if user:
        user_dir = ROOT / "uploads" / f"user_{user.id}"
        user_dir.mkdir(parents=True, exist_ok=True)
        stored = user_dir / f"{datetime.now():%Y%m%d_%H%M%S_%f}{suffix}"
        stored.write_bytes(content)
        db.add(
            Recognition(
                user_id=user.id,
                object_id=attraction.id if attraction else None,
                object_name=attraction.name if attraction else None,
                confidence=float(payload["confidence"]),
                image_url=f"/uploads/user_{user.id}/{stored.name}",
            )
        )
        db.commit()
    return payload


@app.post("/api/plan-route")
def plan_route(request: RouteRequest):
    remaining = [
        item
        for item in catalog_map().values()
        if item.latitude is not None and item.longitude is not None
    ]
    route = []
    current_lat, current_lon = request.latitude, request.longitude
    total = 0.0
    while remaining and len(route) < request.limit:
        nearest = min(
            remaining,
            key=lambda item: haversine(current_lat, current_lon, item.latitude, item.longitude),
        )
        distance = haversine(current_lat, current_lon, nearest.latitude, nearest.longitude)
        route.append({**public_object(nearest), "distance_from_previous_km": round(distance, 2)})
        total += distance
        current_lat, current_lon = nearest.latitude, nearest.longitude
        remaining.remove(nearest)
    return {
        "success": bool(route),
        "start": request.model_dump(exclude={"limit"}),
        "route": route,
        "total_distance_km": round(total, 2),
    }


@app.post("/api/objects", dependencies=[Depends(require_admin)])
async def add_object(
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form("other"),
    municipality: str = Form(...),
    address: str = Form(""),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
    images: list[UploadFile] = File(...),
):
    objects = load_catalog(settings.absolute(settings.catalog_path))
    new_id = max(item.id for item in objects) + 1
    slug = "object-" + str(new_id)
    item = Attraction(
        id=new_id,
        slug=slug,
        name=name,
        category=category,
        municipality=municipality,
        address=address,
        latitude=latitude,
        longitude=longitude,
        description=description,
        access_notes="",
        source_urls=[],
        search_queries=[],
        enabled=True,
        index_status="pending_index",
    )
    manifest = Manifest(settings.absolute(settings.manifest_path))
    target_dir = ROOT / "dataset" / "processed" / f"{new_id:03d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    saved = 0
    for upload in images:
        content = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
        try:
            import io

            with Image.open(io.BytesIO(content)) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGB")
            digest = hashlib.sha256(content).hexdigest()
            path = target_dir / f"{digest}.jpg"
            image.thumbnail((2048, 2048))
            image.save(path, "JPEG", quality=92)
        except (UnidentifiedImageError, OSError):
            continue
        manifest.add(
            {
                "object_id": new_id,
                "object_name": name,
                "source_provider": "admin_upload",
                "source_page_url": "",
                "image_url": upload.filename or "",
                "author": "admin",
                "license": "provided_by_rights_holder",
                "rights_holder": "admin",
                "rights_status": "cleared",
                "retrieved_at": datetime.now(UTC).isoformat(),
                "sha256": digest,
                "width": image.width,
                "height": image.height,
                "mime_type": "image/jpeg",
                "processed_path": path.relative_to(ROOT).as_posix(),
                "status": "accepted",
            }
        )
        saved += 1
    assign_splits(manifest)
    manifest.save()
    objects.append(item)
    save_catalog(settings.absolute(settings.catalog_path), objects)
    searcher.reload()
    return {
        "success": True,
        "object": public_object(item),
        "images_saved": saved,
        "index_status": "pending_index",
    }


@app.put("/api/objects/{object_id}", dependencies=[Depends(require_admin)])
def edit_object(
    object_id: int,
    name: str | None = Form(None),
    description: str | None = Form(None),
    address: str | None = Form(None),
    latitude: float | None = Form(None),
    longitude: float | None = Form(None),
):
    objects = load_catalog(settings.absolute(settings.catalog_path))
    found = False
    for index, item in enumerate(objects):
        if item.id == object_id:
            update = {"index_status": "pending_index"}
            for key, value in {
                "name": name,
                "description": description,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
            }.items():
                if value is not None:
                    update[key] = value
            objects[index] = item.model_copy(update=update)
            found = True
            break
    if not found:
        raise HTTPException(404, "Объект не найден")
    save_catalog(settings.absolute(settings.catalog_path), objects)
    searcher.reload()
    return {"success": True, "object_id": object_id, "index_status": "pending_index"}


def rebuild_index_task() -> None:
    with index_lock:
        index_state.update(running=True, error="", finished_at=None)
        try:
            build_faiss_index(settings.device)
            searcher.reload()
        except Exception as error:
            index_state["error"] = str(error)
        finally:
            index_state.update(running=False, finished_at=datetime.now(UTC).isoformat())


@app.post("/api/admin/reindex", dependencies=[Depends(require_admin)])
def reindex(background_tasks: BackgroundTasks):
    if index_state["running"]:
        raise HTTPException(409, "Индексация уже выполняется")
    index_state["running"] = True
    background_tasks.add_task(rebuild_index_task)
    return {"success": True, "index_status": "building"}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    examples = examples_by_object()
    objects = catalog_map()
    return {
        "objects": len(objects),
        "images": sum(len(items) for items in examples.values()),
        "users": len(db.scalars(select(User)).all()),
        "index_ready": searcher.ready,
        "index_state": index_state,
        "model": f"{settings.model_name}:{settings.model_pretrained}",
    }


@app.get("/health")
def health():
    return {
        "status": "ready" if searcher.quality_ready else "degraded",
        "app": settings.app_name,
        "index_ready": searcher.ready,
        "index_reason": searcher.reason,
        "quality_ready": searcher.quality_ready,
        "quality": {
            "top1_accuracy": searcher.metadata.get("test_metrics", {}).get(
                "top1_accuracy", 0
            ),
            "macro_recall": searcher.metadata.get("test_metrics", {}).get(
                "macro_recall", 0
            ),
            "false_accept_rate": searcher.metadata.get("calibration", {}).get(
                "validation_false_accept_rate", 1
            ),
            "released_classes": len(searcher.metadata.get("ready_object_ids", [])),
        },
        "index_version": str(searcher.metadata.get("manifest_sha256", ""))[:12],
        "index_state": index_state,
    }


def run() -> None:
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    run()
