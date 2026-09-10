#!/usr/bin/env python3
"""
Скрипт для перестройки FAISS индекса на новом датасете туристических достопримечательностей.

Факультет Искусственного Интеллекта РУДН
"""

import os
import pickle
from pathlib import Path
from tqdm import tqdm
import numpy as np
import torch
import clip
from PIL import Image
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.embeddings import Embeddings


class CLIPImageEmbeddings(Embeddings):
    """CLIP embeddings для изображений."""
    
    def __init__(self, device):
        self.device = device
        self.model, self.preprocess = clip.load("ViT-B/16", device=self.device)

    def embed_documents(self, texts):
        raise NotImplementedError

    def embed_query(self, image_path):
        return self.vectorize_img(image_path)

    def vectorize_img(self, img_path):
        """Векторизует изображение через CLIP."""
        img = self.preprocess(Image.open(img_path)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            embedding = self.model.encode_image(img)
        embedding /= np.linalg.norm(embedding)
        return embedding.cpu().numpy()


def build_index_from_dataset(dataset_dir: str = "dataset", 
                             output_dir: str = "artifacts/db",
                             device: str = "cpu"):
    """
    Строит FAISS индекс из датасета.
    
    Args:
        dataset_dir: Путь к папке с датасетом
        output_dir: Путь для сохранения индекса
        device: Устройство для обработки (cpu/cuda)
    """
    print("🚀 Начинаю построение индекса FAISS...")
    print(f"   Датасет: {dataset_dir}")
    print(f"   Выходная папка: {output_dir}")
    print(f"   Устройство: {device}\n")
    
    # Инициализация CLIP
    print("📦 Загружаю модель CLIP...")
    embedder = CLIPImageEmbeddings(device=device)
    print("✅ Модель CLIP загружена\n")
    
    # Собираем все изображения из датасета (только ground, без aerial)
    print("📂 Собираю изображения из датасета...")
    dataset_path = Path(dataset_dir)
    
    if not dataset_path.exists():
        raise FileNotFoundError(f"Папка датасета не найдена: {dataset_dir}")
    
    image_files = []
    
    for folder in sorted(dataset_path.iterdir()):
        if not folder.is_dir():
            continue
        
        folder_name = folder.name
        
        # Пропускаем если имя папки не начинается с цифр
        if not folder_name[0:2].isdigit():
            continue
        
        # Собираем изображения из корня папки
        for img_file in sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.jpeg")):
            if img_file.is_file():
                # Относительный путь для сохранения в индексе
                rel_path = f"{folder_name}/{img_file.name}"
                image_files.append((str(img_file.absolute()), rel_path))
        
        # Собираем изображения из подпапки ground (без aerial)
        ground_dir = folder / "ground"
        if ground_dir.exists() and ground_dir.is_dir():
            for img_file in sorted(ground_dir.glob("*.jpg")) + sorted(ground_dir.glob("*.jpeg")):
                if img_file.is_file():
                    # Относительный путь для сохранения в индексе
                    rel_path = f"{folder_name}/ground/{img_file.name}"
                    image_files.append((str(img_file.absolute()), rel_path))
    
    print(f"✅ Найдено {len(image_files)} изображений для индексации\n")
    
    if not image_files:
        raise ValueError("Не найдено изображений в датасете!")
    
    # Создаем эмбеддинги для всех изображений
    print("🔄 Создаю эмбеддинги...")
    embeddings_list = []
    file_names_list = []
    
    for img_path, rel_path in tqdm(image_files, desc="Обработка изображений"):
        try:
            embedding = embedder.vectorize_img(img_path)
            embeddings_list.append(embedding)
            file_names_list.append(rel_path)
        except Exception as e:
            print(f"⚠️ Ошибка при обработке {img_path}: {e}")
            continue
    
    if not embeddings_list:
        raise ValueError("Не удалось создать эмбеддинги!")
    
    print(f"✅ Создано {len(embeddings_list)} эмбеддингов\n")
    
    # Преобразуем в numpy массивы
    embeddings = np.array(embeddings_list).squeeze()
    
    # Нормализуем эмбеддинги
    print("📊 Нормализую эмбеддинги...")
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized_embeddings = embeddings / norms
    print("✅ Нормализация завершена\n")
    
    # Создаем FAISS индекс
    print("🏗️ Создаю FAISS индекс...")
    vectorstore = FAISS.from_embeddings(
        text_embeddings=list(zip(file_names_list, normalized_embeddings)),
        embedding=embedder,
        distance_strategy=DistanceStrategy.COSINE,
    )
    print("✅ FAISS индекс создан\n")
    
    # Сохраняем индекс
    print(f"💾 Сохраняю индекс в {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    vectorstore.save_local(output_dir)
    print(f"✅ Индекс сохранен в {output_dir}\n")
    
    # Показываем статистику
    print("="*70)
    print("📊 СТАТИСТИКА ИНДЕКСА")
    print("="*70)
    print(f"   Всего изображений: {len(file_names_list)}")
    print(f"   Размерность эмбеддингов: {normalized_embeddings.shape}")
    print(f"   Путь к индексу: {output_dir}")
    print("="*70)
    
    # Показываем примеры путей
    print("\n📋 Примеры путей в индексе (первые 10):")
    for i, path in enumerate(file_names_list[:10], 1):
        print(f"   {i}. {path}")
    
    print("\n✅ Индекс успешно построен!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Построение FAISS индекса из датасета")
    parser.add_argument("--dataset", type=str, default="dataset", 
                       help="Путь к папке с датасетом (по умолчанию: dataset)")
    parser.add_argument("--output", type=str, default="artifacts/db",
                       help="Путь для сохранения индекса (по умолчанию: artifacts/db)")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "cuda"],
                       help="Устройство для обработки (по умолчанию: cpu)")
    
    args = parser.parse_args()
    
    try:
        build_index_from_dataset(
            dataset_dir=args.dataset,
            output_dir=args.output,
            device=args.device
        )
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

