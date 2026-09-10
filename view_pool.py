#!/usr/bin/env python3
"""
Скрипт для тестирования системы распознавания и просмотра пула хорошо распознанных изображений.

Факультет Искусственного Интеллекта РУДН
"""

import os
from pathlib import Path
from PIL import Image
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import sys

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_searcher import RAGSearcher


def test_dataset(ragger: RAGSearcher, top_k: int = 3) -> Dict:
    """
    Тестирует систему распознавания на всем датасете.
    
    Args:
        ragger: Инициализированный RAGSearcher
        top_k: Количество топ результатов для проверки (правильный ответ должен быть в топ-k)
    
    Returns:
        Словарь со статистикой тестирования
    """
    dataset_dir = Path("dataset")
    
    if not dataset_dir.exists():
        print("❌ Папка dataset не найдена")
        return {}
    
    print("🧪 Начинаю тестирование системы распознавания...")
    print(f"   Проверяю топ-{top_k} результатов для каждого изображения\n")
    
    # Собираем все изображения из датасета (только ground, без aerial)
    test_cases = []
    
    for folder in sorted(dataset_dir.iterdir()):
        if not folder.is_dir():
            continue
        
        # Извлекаем ID из имени папки (формат: XX_Название)
        folder_name = folder.name
        if not folder_name[0:2].isdigit():
            continue
        
        try:
            expected_id = int(folder_name.split('_')[0])
        except ValueError:
            continue
        
        # Собираем изображения из корня папки
        for img_file in sorted(folder.glob("*.jpg")) + sorted(folder.glob("*.jpeg")):
            if img_file.is_file():
                test_cases.append({
                    "path": str(img_file),
                    "expected_id": expected_id,
                    "folder": folder_name
                })
        
        # Собираем изображения из подпапки ground (без aerial)
        ground_dir = folder / "ground"
        if ground_dir.exists() and ground_dir.is_dir():
            for img_file in sorted(ground_dir.glob("*.jpg")) + sorted(ground_dir.glob("*.jpeg")):
                if img_file.is_file():
                    test_cases.append({
                        "path": str(img_file),
                        "expected_id": expected_id,
                        "folder": folder_name
                    })
    
    print(f"📊 Найдено {len(test_cases)} изображений для тестирования\n")
    
    # Статистика
    stats = {
        "total": len(test_cases),
        "correct_top1": 0,
        "correct_top3": 0,
        "incorrect": 0,
        "by_object": defaultdict(lambda: {"total": 0, "correct_top1": 0, "correct_top3": 0, "incorrect": 0}),
        "errors": []
    }
    
    # Тестируем каждое изображение
    for idx, test_case in enumerate(test_cases, 1):
        img_path = test_case["path"]
        expected_id = test_case["expected_id"]
        folder_name = test_case["folder"]
        
        # Обновляем статистику по объектам
        stats["by_object"][expected_id]["total"] += 1
        
        try:
            # Получаем вектор запроса через embed_query (возвращает numpy array)
            query_vector = ragger.embedder.embed_query(img_path)
            
            # Преобразуем в правильный формат для FAISS
            if hasattr(query_vector, 'flatten'):
                query_vector_flat = query_vector.flatten()
            else:
                query_vector_flat = query_vector
            
            # Ищем топ-k результатов
            results = ragger.vectorstore.similarity_search_with_score_by_vector(
                query_vector_flat, k=top_k
            )
            
            if not results:
                stats["incorrect"] += 1
                stats["by_object"][expected_id]["incorrect"] += 1
                stats["errors"].append({
                    "path": img_path,
                    "expected": expected_id,
                    "got": None,
                    "reason": "No results found"
                })
                continue
            
            # Извлекаем ID из результатов (используем ту же логику что и в rag_searcher)
            found_ids = []
            import re
            for doc, score in results:
                # Парсим ID из пути файла
                filepath = doc.page_content
                class_id = None
                
                # Try new format: dataset/XX_Name/photo_X.jpg
                if 'dataset/' in filepath:
                    parts = filepath.split('/')
                    for part in parts:
                        if part.startswith('dataset'):
                            continue
                        # Look for pattern like "01_Название"
                        if '_' in part:
                            num_part = part.split('_')[0]
                            try:
                                class_id = int(num_part)
                                break
                            except ValueError:
                                continue
                
                # Try old format: OXXXX_YYYYYY.jpg
                if class_id is None and '_' in filepath:
                    filename = filepath.split('/')[-1]
                    if filename.startswith('O') and '_' in filename:
                        class_id_str = filename.split("_")[0][1:]
                        try:
                            class_id = int(class_id_str)
                        except ValueError:
                            pass
                
                # If still not found, try regex
                if class_id is None:
                    match = re.search(r'(\d+)_', filepath)
                    if match:
                        class_id = int(match.group(1))
                
                if class_id is not None:
                    found_ids.append((class_id, score))
            
            # Проверяем результаты
            found_ids_only = [id for id, _ in found_ids]
            
            # Топ-1 правильный
            if found_ids_only and found_ids_only[0] == expected_id:
                stats["correct_top1"] += 1
                stats["by_object"][expected_id]["correct_top1"] += 1
                if expected_id in found_ids_only[:top_k]:
                    stats["correct_top3"] += 1
                    stats["by_object"][expected_id]["correct_top3"] += 1
            # Правильный ответ в топ-3
            elif expected_id in found_ids_only[:top_k]:
                stats["correct_top3"] += 1
                stats["by_object"][expected_id]["correct_top3"] += 1
            else:
                stats["incorrect"] += 1
                stats["by_object"][expected_id]["incorrect"] += 1
                got_id = found_ids_only[0] if found_ids_only else None
                stats["errors"].append({
                    "path": img_path,
                    "expected": expected_id,
                    "got": got_id,
                    "top3": found_ids_only[:top_k],
                    "scores": [f"{score:.4f}" for _, score in found_ids[:top_k]]
                })
            
            # Прогресс
            if idx % 50 == 0:
                print(f"   Обработано: {idx}/{len(test_cases)} ({idx*100//len(test_cases)}%)")
        
        except Exception as e:
            stats["incorrect"] += 1
            stats["by_object"][expected_id]["incorrect"] += 1
            stats["errors"].append({
                "path": img_path,
                "expected": expected_id,
                "error": str(e)
            })
            print(f"   ⚠️ Ошибка при обработке {img_path}: {e}")
    
    return stats


def print_test_results(stats: Dict):
    """Выводит результаты тестирования."""
    if not stats:
        return
    
    print("\n" + "="*70)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*70)
    
    total = stats["total"]
    correct_top1 = stats["correct_top1"]
    correct_top3 = stats["correct_top3"]
    incorrect = stats["incorrect"]
    
    print(f"\n📈 Общая статистика:")
    print(f"   Всего изображений: {total}")
    print(f"   ✅ Правильно (топ-1): {correct_top1} ({correct_top1*100/total:.1f}%)")
    print(f"   ✅ Правильно (топ-{3}): {correct_top3} ({correct_top3*100/total:.1f}%)")
    print(f"   ❌ Неправильно: {incorrect} ({incorrect*100/total:.1f}%)")
    
    print(f"\n📋 Статистика по объектам:")
    print(f"{'ID':<4} {'Название':<35} {'Всего':<8} {'Топ-1':<8} {'Топ-3':<8} {'Ошибок':<8} {'Точность':<10}")
    print("-" * 90)
    
    # Загружаем названия объектов
    try:
        with open("artifacts_turism/turism.json", "r", encoding="utf-8") as f:
            objects_data = json.load(f)
            objects_dict = {obj["id"]: obj.get("Название", f"Объект {obj['id']}") for obj in objects_data}
    except Exception:
        objects_dict = {}
    
    for obj_id in sorted(stats["by_object"].keys()):
        obj_stats = stats["by_object"][obj_id]
        name = objects_dict.get(obj_id, f"Объект {obj_id}")
        name = (name[:33] + "...") if len(name) > 35 else name
        
        total_obj = obj_stats["total"]
        correct_top1_obj = obj_stats["correct_top1"]
        correct_top3_obj = obj_stats["correct_top3"]
        incorrect_obj = obj_stats["incorrect"]
        
        accuracy = (correct_top3_obj * 100 / total_obj) if total_obj > 0 else 0
        
        print(f"{obj_id:<4} {name:<35} {total_obj:<8} {correct_top1_obj:<8} {correct_top3_obj:<8} {incorrect_obj:<8} {accuracy:.1f}%")
    
    # Показываем примеры ошибок
    if stats["errors"]:
        print(f"\n⚠️ Примеры ошибок (первые 10):")
        for i, error in enumerate(stats["errors"][:10], 1):
            print(f"   {i}. Ожидался ID {error['expected']}, получен: {error.get('got', 'N/A')}")
            if 'top3' in error:
                print(f"      Топ-3: {error['top3']} (scores: {', '.join(error.get('scores', []))})")
            print(f"      Путь: {Path(error['path']).name}")
    
    print("\n" + "="*70)


def view_pool():
    """Просмотр содержимого пула хорошо распознанных изображений."""
    pool_dir = Path("pool/recognized")
    
    if not pool_dir.exists():
        print("❌ Пул распознанных изображений не найден")
        print(f"   Создайте папку: {pool_dir}")
        return
    
    images = list(pool_dir.glob("*.jpg")) + list(pool_dir.glob("*.jpeg"))
    
    if not images:
        print("📭 Пул пуст - еще нет хорошо распознанных изображений")
        return
    
    print(f"📊 Пул хорошо распознанных изображений: {len(images)} изображений\n")
    
    # Группируем по объектам
    objects_stats = defaultdict(list)
    for img_path in images:
        # Формат имени: obj_XX_dist_YYYY_datestring.jpg
        parts = img_path.stem.split('_')
        if len(parts) >= 2 and parts[0] == 'obj':
            try:
                obj_id = int(parts[1])
                objects_stats[obj_id].append(img_path)
            except ValueError:
                continue
    
    # Загружаем описания объектов
    try:
        with open("artifacts_turism/turism.json", "r", encoding="utf-8") as f:
            objects_data = json.load(f)
            objects_dict = {obj["id"]: obj for obj in objects_data}
    except Exception as e:
        print(f"⚠️ Не удалось загрузить описания объектов: {e}")
        objects_dict = {}
    
    # Выводим статистику
    print("📈 Статистика по объектам:")
    for obj_id in sorted(objects_stats.keys()):
        count = len(objects_stats[obj_id])
        obj_name = objects_dict.get(obj_id, {}).get("Название", f"Объект {obj_id}")
        print(f"   ID {obj_id:2d}: {obj_name[:50]:50s} - {count:3d} изображений")
    
    print(f"\n💾 Все изображения сохранены в: {pool_dir.absolute()}")


def main():
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Тестирование системы распознавания и просмотр пула")
    parser.add_argument("--test", action="store_true", help="Запустить тестирование датасета")
    parser.add_argument("--view", action="store_true", help="Просмотреть пул распознанных изображений")
    parser.add_argument("--top-k", type=int, default=3, help="Количество топ результатов для проверки (по умолчанию 3)")
    
    args = parser.parse_args()
    
    if args.test:
        print("🚀 Инициализация RAG searcher...")
        try:
            ragger = RAGSearcher(
                device="cpu",
                vectorstore_path="artifacts/db",
                object_descr_path="artifacts_turism/turism.json",
                similarity_threshold=0.9
            )
            print("✅ RAG searcher инициализирован\n")
            
            # Запускаем тестирование
            stats = test_dataset(ragger, top_k=args.top_k)
            print_test_results(stats)
            
        except Exception as e:
            print(f"❌ Ошибка инициализации: {e}")
            import traceback
            traceback.print_exc()
    
    elif args.view:
        view_pool()
    
    else:
        # По умолчанию показываем оба
        print("="*70)
        print("ТЕСТИРОВАНИЕ СИСТЕМЫ РАСПОЗНАВАНИЯ")
        print("="*70)
        print("\n🚀 Инициализация RAG searcher...")
        try:
            ragger = RAGSearcher(
                device="cpu",
                vectorstore_path="artifacts/db",
                object_descr_path="artifacts_turism/turism.json",
                similarity_threshold=0.9
            )
            print("✅ RAG searcher инициализирован\n")
            
            # Запускаем тестирование
            stats = test_dataset(ragger, top_k=args.top_k)
            print_test_results(stats)
            
            print("\n" + "="*70)
            print("ПРОСМОТР ПУЛА РАСПОЗНАННЫХ ИЗОБРАЖЕНИЙ")
            print("="*70 + "\n")
            view_pool()
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
