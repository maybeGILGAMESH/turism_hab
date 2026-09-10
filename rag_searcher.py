"""
RAG (Retrieval-Augmented Generation) searcher for North Caucasus tourist attractions.

This module provides functionality to search and retrieve information about tourist
attractions in North Caucasus using CLIP embeddings and FAISS vector search.

Факультет Искусственного Интеллекта РУДН
"""

import json
import os
import re
from collections import defaultdict
from typing import List, Tuple, Optional, Union, Dict, Any

import clip
import numpy as np
import torch
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from PIL import Image


class CLIPImageEmbeddings(Embeddings):
    """
    CLIP-based image embeddings for similarity search.
    
    This class implements the Embeddings interface from LangChain to provide
    CLIP-based image vectorization capabilities for the RAG system.
    
    Attributes:
        device (str): Device to run the CLIP model on ('cpu' or 'cuda')
        model: The loaded CLIP model
        preprocess: The CLIP image preprocessing function
    """
    
    def __init__(self, device: str) -> None:
        """
        Initialize the CLIP image embeddings.
        
        Args:
            device: Device to run the CLIP model on ('cpu' or 'cuda')
            
        Raises:
            Exception: If CLIP model fails to load
        """
        self.device = device
        try:
            self.model, self.preprocess = clip.load("ViT-B/16", device=self.device)
            print(f"✅ CLIP model loaded successfully on {device}")
        except Exception as e:
            print(f"❌ Error loading CLIP model: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of text documents.
        
        This method is not implemented as this class is designed for image embeddings only.
        
        Args:
            texts: List of text documents to embed
            
        Raises:
            NotImplementedError: This method is not supported for image embeddings
        """
        raise NotImplementedError("Text embedding not supported for CLIP image embeddings")

    def embed_query(self, image_path: str) -> np.ndarray:
        """
        Embed a single image query.
        
        Args:
            image_path: Path to the image file to embed
            
        Returns:
            Normalized image embedding vector
            
        Raises:
            FileNotFoundError: If the image file doesn't exist
            Exception: If image processing fails
        """
        return self.vectorize_img(image_path)

    def vectorize_img(self, img_path: str) -> np.ndarray:
        """
        Convert an image to a normalized embedding vector.
        
        Args:
            img_path: Path to the image file
            
        Returns:
            Normalized image embedding vector as numpy array
            
        Raises:
            FileNotFoundError: If the image file doesn't exist
            Exception: If image processing or model inference fails
        """
        try:
            # Check if file exists
            if not os.path.exists(img_path):
                raise FileNotFoundError(f"Image file not found: {img_path}")
            
            # Preprocess image and get embedding
            img = self.preprocess(Image.open(img_path)).unsqueeze(0).to(self.device)
            with torch.no_grad():
                embedding = self.model.encode_image(img)
            embedding /= np.linalg.norm(embedding)
            return embedding.cpu().numpy()
        except Exception as e:
            print(f"❌ Error processing image {img_path}: {e}")
            raise


class RAGSearcher:
    """
    RAG searcher for North Caucasus tourist attractions.
    
    This class provides functionality to search for tourist attractions
    using CLIP embeddings and FAISS vector similarity search.
    
    Attributes:
        device (str): Device to run the CLIP model on
        embedder (CLIPImageEmbeddings): CLIP image embedding model
        vectorstore (FAISS): FAISS vector database for similarity search
        descriptor (Dict[str, str]): Dictionary mapping object IDs to descriptions
    """
    
    def __init__(self, device: str, vectorstore_path: str, object_descr_path: str, 
                 similarity_threshold: float = 0.5) -> None:
        """
        Initialize the RAG searcher.
        
        Args:
            device: Device to run the CLIP model on ('cpu' or 'cuda')
            vectorstore_path: Path to the FAISS vector database
            object_descr_path: Path to the JSON file containing object descriptions
            similarity_threshold: Maximum distance threshold for recognition (default: 0.5)
                                  If best match distance exceeds this, object is not recognized
            
        Raises:
            FileNotFoundError: If required files don't exist
            Exception: If initialization fails
        """
        try:
            self.device = device
            self.embedder = CLIPImageEmbeddings(device)
            self.similarity_threshold = similarity_threshold
            
            # Check if vectorstore path exists
            if not os.path.exists(vectorstore_path):
                raise FileNotFoundError(f"Vectorstore path not found: {vectorstore_path}")
            
            self.vectorstore = FAISS.load_local(
                vectorstore_path, self.embedder, allow_dangerous_deserialization=True
            )
            print(f"✅ FAISS vectorstore loaded from {vectorstore_path}")
            
            # Check if descriptor file exists
            if not os.path.exists(object_descr_path):
                raise FileNotFoundError(f"Object descriptor file not found: {object_descr_path}")
            
            with open(object_descr_path, 'r', encoding='utf-8') as json_data:
                data = json.load(json_data)
            
            # Поддержка как старого формата (словарь), так и нового (массив)
            if isinstance(data, list):
                # Новый формат: массив объектов
                self.descriptor = {}
                for obj in data:
                    obj_id = str(obj.get("id", ""))
                    # Формируем описание из полей объекта
                    description = f"Название: {obj.get('Название', '')}\n"
                    description += f"Местоположение: {obj.get('Местоположение', '')}\n"
                    description += f"\nКраткая историческая справка:\n{obj.get('Краткая историческая справка', '')}"
                    self.descriptor[obj_id] = description
            else:
                # Старый формат: словарь
                self.descriptor = data
            
            print(f"✅ Object descriptors loaded: {len(self.descriptor)} objects")
            print(f"✅ Similarity threshold: {similarity_threshold}")
            
        except Exception as e:
            print(f"❌ Error initializing RAG searcher: {e}")
            raise

    def search(self, query_path: str) -> Optional[Tuple[int, float]]:
        """
        Search for the most similar tourist attraction.
        
        Args:
            query_path: Path to the query image file
            
        Returns:
            Tuple of (Object ID, distance) if found, None otherwise
            
        Raises:
            Exception: If search process fails
        """
        try:
            # Get query vector
            query_vector = self.embedder.embed_query(query_path)
            
            # Search for similar vectors
            results = self.vectorstore.similarity_search_with_score_by_vector(
                query_vector.flatten(), k=5
            )
            
            if not results:
                print("⚠️ No search results found")
                return None
            
            # Find best class ID and distance
            result = self._find_best_class_id(results)
            
            if result is not None:
                class_id, distance = result
                print(f"✅ Found best class ID: {class_id}")
                return (class_id, distance)
            else:
                print("⚠️ No suitable class found")
                return None
                
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return None

    def _find_best_class_id(self, results: List[Tuple[Document, float]]) -> Optional[Tuple[int, float]]:
        """
        Analyze search results to find the class with the lowest cumulative distance.
        
        Supports both old format (OXXXX_YYYYYY.jpg) and new format (dataset/XX_Name/photo_X.jpg).
        
        Args:
            results: List of tuples containing Document objects and distance scores
            
        Returns:
            Tuple of (Integer ID, distance) of the class with the least cumulative distance, or None if parsing fails
            
        Raises:
            Exception: If analysis process fails
        """
        try:
            if not results:
                return None
                
            class_scores: Dict[int, float] = {}
            class_counts: Dict[int, int] = defaultdict(int)

            for doc, score in results:
                try:
                    # Parse the class ID from the filename/path
                    filepath = doc.page_content
                    if not filepath:
                        print(f"⚠️ Empty filepath: {filepath}")
                        continue
                    
                    class_id = None
                    
                    # Try new format: dataset/XX_Name/photo_X.jpg or dataset/XX_Name/subfolder/photo_X.jpg
                    if 'dataset/' in filepath:
                        # Extract folder name from path like dataset/01_Название/photo_X.jpg
                        parts = filepath.split('/')
                        for part in parts:
                            if part.startswith('dataset'):
                                continue
                            # Look for pattern like "01_Название" or "01_Название_Дербент"
                            if '_' in part:
                                # Extract number from start (e.g., "01" from "01_Название")
                                num_part = part.split('_')[0]
                                try:
                                    class_id = int(num_part)
                                    break
                                except ValueError:
                                    continue
                    
                    # Try old format: OXXXX_YYYYYY.jpg
                    if class_id is None and '_' in filepath:
                        filename = filepath.split('/')[-1]  # Get just filename
                        if filename.startswith('O') and '_' in filename:
                            class_id_str = filename.split("_")[0][1:]  # Remove 'O' prefix
                            class_id = int(class_id_str)
                    
                    # If still not found, try to extract from any numeric prefix
                    if class_id is None:
                        # Try to find any number at the start of filename or path
                        match = re.search(r'(\d+)_', filepath)
                        if match:
                            class_id = int(match.group(1))
                    
                    if class_id is None:
                        print(f"⚠️ Could not extract class ID from: {filepath}")
                        continue
                    
                    # Track minimum distance (best match) for each class
                    # Lower distance = better match
                    if class_id not in class_scores or score < class_scores[class_id]:
                        class_scores[class_id] = score
                    class_counts[class_id] += 1
                    
                except (ValueError, IndexError) as e:
                    print(f"⚠️ Error parsing filepath {doc.page_content}: {e}")
                    continue

            if not class_scores:
                return None
            
            # Улучшенная логика выбора лучшего класса
            # Учитываем не только минимальное расстояние, но и количество совпадений
            # Если разница между классами мала (< 0.05), предпочитаем класс с большим количеством совпадений
            
            # Сортируем классы по расстоянию
            sorted_classes = sorted(class_scores.items(), key=lambda x: (x[1], -class_counts[x[0]]))
            
            if len(sorted_classes) > 1:
                best_score_diff = sorted_classes[1][1] - sorted_classes[0][1]
                # Если разница между лучшими классами очень мала (< 0.05), 
                # предпочитаем класс с большим количеством совпадений
                if best_score_diff < 0.05:
                    # Сортируем по количеству совпадений, затем по расстоянию
                    sorted_by_count = sorted(class_scores.items(), key=lambda x: (-class_counts[x[0]], x[1]))
                    best_id = sorted_by_count[0][0]
                    best_score = class_scores[best_id]
                else:
                    best_id = sorted_classes[0][0]
                    best_score = sorted_classes[0][1]
            else:
                best_id = sorted_classes[0][0]
                best_score = sorted_classes[0][1]
            
            # Выводим информацию о распознавании
            print(f"🔍 Recognition result: ID {best_id}, distance {best_score:.4f} (threshold: {self.similarity_threshold}, count: {class_counts[best_id]})")
            
            # Check if the best match is good enough
            if best_score > self.similarity_threshold:
                print(f"⚠️ Best match distance {best_score:.4f} exceeds threshold {self.similarity_threshold}")
                print(f"   Attraction not recognized - likely not from North Caucasus tourist attractions")
                return None
            
            return (best_id, best_score)
            
        except Exception as e:
            print(f"❌ Error in _find_best_class_id: {e}")
            return None

    def get_description(self, class_name: int) -> str:
        """
        Get the description for a specific tourist attraction.
        
        Args:
            class_name: Integer ID of the tourist attraction
            
        Returns:
            Description string for the object, or error message if not found
            
        Raises:
            Exception: If description retrieval fails
        """
        try:
            class_key = str(class_name)
            if class_key in self.descriptor:
                return self.descriptor[class_key]
            else:
                print(f"⚠️ Class {class_name} not found in descriptor")
                return f"Описание для объекта {class_name} недоступно"
        except Exception as e:
            print(f"❌ Error getting description for class {class_name}: {e}")
            return f"Ошибка получения описания для объекта {class_name}"
