import pickle
from sentence_transformers import SentenceTransformer, util
import torch
import sqlite3
import os
import re
from typing import List, Dict, Tuple
from flask import jsonify
import requests
import gdown


class SemanticSearch:
    def __init__(self, db_path: str):
        self.db_path = db_path
        try:

            print("Loading SentenceTransformer model...")
            self.model = SentenceTransformer('all-MiniLM-L12-v1')
            print("Model loaded.")
            self.embeddings_cache = {}
            self.meta_cache = {}  # Кэш для метаданных (например, file_date)
            if os.path.exists("embeddings_cache.pkl"):
                self._load_embeddings_from_cache()
            else:
                print("Cache file not found locally. Downloading from Google Drive...")
                self.download_embeddings_cache()
                self._load_embeddings_from_cache()

            #self._load_embeddings()
            #rint("Embeddings loaded.")
            #self.cache_to_save()

            # self._load_embeddings()
            # print("Embeddings loaded.")
            # self.cache_to_save()
            print("Saved cache to embeddings_cache.pkl.")

        except Exception as e:
            print("Error in SemanticSearch __init__:", e)
            raise

    def cache_to_save(self):
        try:
            print("Saving embeddings cache...")
            cache_to_save = {
                id: embedding.cpu().numpy()  # Убираем с GPU и делаем numpy
                for id, embedding in self.embeddings_cache.items()
            }
            # Сохраняем в файл
            with open("embeddings_cache.pkl", "wb") as f:
                pickle.dump(cache_to_save, f)
            print("Кэш сохранён в embeddings_cache.pkl")
        except Exception as e:
            print("Error in cache_to_save:", e)
            raise

    def download_embeddings_cache(self):
        file_id = "1JQOYyE75EF257d2Z3zEzmc87iraKYq91"  # Замени на свой file_id
        output = "embeddings_cache.pkl"
        if not os.path.exists(output):
            print("Cache file not found locally. Downloading from Google Drive via gdown...")
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, output, quiet=False)
            print("Download complete.")
        else:
            print("Cache file already exists locally.")

    def _load_embeddings_from_cache(self, cache_path: str = "embeddings_cache.pkl"):
        try:
            print(f"Загрузка кэша из {cache_path}...")
            with open(cache_path, "rb") as f:
                cached_data = pickle.load(f)
            print(f"Загружено {len(cached_data)} эмбеддингов.")

            # Загружаем эмбеддинги обратно в тензоры
            for id, embedding_array in cached_data.items():
                self.embeddings_cache[id] = torch.tensor(embedding_array)

            # Загружаем метаданные из базы данных (они нужны для поиска)
            print("Загрузка метаданных из базы данных...")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, filename, detected_text, detected_objects, file_date, has_faces
                FROM image_data
            """)
            records = cursor.fetchall()
            conn.close()

            for record in records:
                id, filename, detected_text, detected_objects, file_date, has_faces = record
                self.meta_cache[id] = {
                    'filename': filename,
                    'file_date': file_date,
                    'detected_objects': detected_objects,
                    'has_faces': has_faces,
                    'detected_text': detected_text
                }
            print("Метаданные успешно загружены.")
        except Exception as e:
            print("Ошибка в _load_embeddings_from_cache:", e)
            raise


    def _load_embeddings(self):
        try:
            print("Connecting to database:", self.db_path)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            print("Connected. Executing SELECT...")
            cursor.execute("""
                SELECT id, filename, detected_text, detected_objects, file_date, has_faces
                FROM image_data
            """)
            records = cursor.fetchall()
            print(f"Fetched {len(records)} records from DB.")
            conn.close()
            texts = []
            for record in records:
                id, filename, detected_text, detected_objects, file_date, has_faces = record
                search_text = f"{filename} {detected_text or ''} {detected_objects or ''}"
                texts.append((id, search_text))
                self.meta_cache[id] = {
                    'filename': filename,
                    'file_date': file_date,
                    'detected_objects': detected_objects,
                    'has_faces': has_faces,
                    'detected_text': detected_text
                }
                print(f"id={id}, detected_text={detected_text}")
            if texts:
                print("Encoding texts...")
                ids, search_texts = zip(*texts)
                print(f"Before embedding")
                embeddings = self.model.encode(search_texts, convert_to_tensor=True)
                print(f"After embedding")
                for id, embedding in zip(ids, embeddings):
                    print(f"id={id}")
                    self.embeddings_cache[id] = embedding
                print("Texts encoded and cached.")
            else:
                print("No texts to encode.")
        except Exception as e:
            print("Error in _load_embeddings:", e)
            raise

    def extract_date_filters(self, query: str):
        # Извлекаем года, месяцы и дни из запроса
        years = re.findall(r'\b(19|20)\d{2}\b', query)
        months = re.findall(r'(?:январ[ья]|феврал[ья]|март[а]?|апрел[ья]|ма[йя]|июн[ья]|июл[ья]|август[а]?|сентябр[ья]|октябр[ья]|ноябр[ья]|декабр[ья]|0[1-9]|1[0-2])', query, re.IGNORECASE)
        days = re.findall(r'\b([0-2][0-9]|3[01])\b', query)
        years = re.findall(r'\b(?:19|20)\d{2}\b', query)
        return years, months, days

    def month_to_number(self, month_str):
        # Преобразует название месяца или номер в формат MM
        months = {
            'январ': '01', 'феврал': '02', 'март': '03', 'апрел': '04', 'май': '05', 'июн': '06',
            'июл': '07', 'август': '08', 'сентябр': '09', 'октябр': '10', 'ноябр': '11', 'декабр': '12',
            # Английские названия
            'january': '01', 'february': '02', 'march': '03', 'april': '04', 'may': '05', 'june': '06',
            'july': '07', 'august': '08', 'september': '09', 'october': '10', 'november': '11', 'december': '12',
            # Числовые значения
            '01': '01', '02': '02', '03': '03', '04': '04', '05': '05', '06': '06',
            '07': '07', '08': '08', '09': '09', '10': '10', '11': '11', '12': '12'
        }
        for key in months:
            if month_str.lower().startswith(key):
                return months[key]
        return None

    def search(self, query: str, top_k: int = 20, offset: int = 0) -> List[Dict]:
        """
        Выполняет семантический поиск по запросу с поддержкой фильтрации по годам, месяцам, дням и ключевым словам
        """
        years, months, days = self.extract_date_filters(query)
        months = [self.month_to_number(m) for m in months if self.month_to_number(m)]

        # Если есть фильтры по дате — сначала фильтруем по дате
        filtered_ids = []
        for id, meta in self.meta_cache.items():
            file_date = meta.get('file_date', '')
            if years and not any(year in file_date for year in years):
                continue
            if months and not any(f'-{month}-' in file_date for month in months):
                continue
            if days and not any(re.search(rf'-{day.zfill(2)}[ T]', file_date) for day in days):
                continue
            filtered_ids.append(id)

        # Если фильтры по дате есть — считаем score только для них, иначе для всех
        if filtered_ids:
            candidates = filtered_ids
        else:
            candidates = list(self.meta_cache.keys())

        query_embedding = self.model.encode(query, convert_to_tensor=True)
        similarities = {}
        for id in candidates:
            embedding = self.embeddings_cache[id]
            similarity = util.pytorch_cos_sim(query_embedding, embedding)[0][0].item()
            similarities[id] = similarity

        sorted_results = sorted(similarities.items(), key=lambda x: x[1], reverse=True)

        results = []
        for id, score in sorted_results[offset:offset+top_k]:
            meta = self.meta_cache.get(id, {})
            print(f"RESULT: id={id}, file_date={meta.get('file_date')}, detected_text={meta.get('detected_text')}")
            results.append({
                'id': id,
                'filename': meta.get('filename', ''),
                'file_date': meta.get('file_date', ''),
                'detected_objects': meta.get('detected_objects', ''),
                'has_faces': meta.get('has_faces', ''),
                'detected_text': meta.get('detected_text') if meta.get('detected_text') else 'No text',
                'relevance_score': score
            })
            if len(results) >= top_k:
                break

        return results

    def search_api(self, query: str, top_k: int = 10):
        try:
            print("Calling semantic_search.search with:", query, top_k)
            results = self.search(query, top_k)
            return jsonify(results)
        except Exception as e:
            print("Error in /api/semantic-search/:", e)
            return jsonify({'error': str(e)}), 400 