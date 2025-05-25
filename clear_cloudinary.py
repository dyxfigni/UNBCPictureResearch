import cloudinary
import cloudinary.uploader
import cloudinary.api
from concurrent.futures import ThreadPoolExecutor
import time
from typing import List, Dict
import math

# Конфигурация Cloudinary
cloudinary.config(
    cloud_name = "ddqjcxii6",  # Используем правильное имя с маленькой буквой i
    api_key = "196691329517392",  # Замените на ваш API ключ
    api_secret = "ebDQHi4E6HWh6Wf7WeRMVEEOLnQ"  # Замените на ваш API секрет
)

def get_all_resources() -> List[Dict]:
    """Получает все ресурсы с Cloudinary"""
    all_resources = []
    next_cursor = None
    
    while True:
        # Получаем ресурсы порциями по 1000
        result = cloudinary.api.resources(
            type="upload",
            max_results=1000,
            next_cursor=next_cursor
        )
        
        all_resources.extend(result['resources'])
        
        # Проверяем, есть ли еще ресурсы
        next_cursor = result.get('next_cursor')
        if not next_cursor:
            break
            
        print(f"Загружено {len(all_resources)} файлов...")
    
    return all_resources

def delete_resources_batch(resources: List[Dict]):
    """Удаляет пакет ресурсов"""
    try:
        # Собираем все public_id в один список
        public_ids = [resource['public_id'] for resource in resources]
        
        # Удаляем все ресурсы в пакете одним запросом
        result = cloudinary.api.delete_resources(public_ids)
        
        # Выводим результат
        deleted = result.get('deleted', {})
        failed = result.get('failed', {})
        
        print(f"Успешно удалено: {len(deleted)} файлов")
        if failed:
            print(f"Ошибки при удалении: {len(failed)} файлов")
            
    except Exception as e:
        print(f"Ошибка при удалении пакета: {e}")

def delete_all_resources():
    try:
        print("Начинаем загрузку списка файлов...")
        start_time = time.time()
        
        # Получаем все ресурсы
        all_resources = get_all_resources()
        total_resources = len(all_resources)
        
        print(f"\nВсего найдено {total_resources} файлов")
        
        # Разбиваем на пакеты по 100 файлов
        batch_size = 100
        num_batches = math.ceil(total_resources / batch_size)
        resource_batches = [
            all_resources[i:i + batch_size] 
            for i in range(0, total_resources, batch_size)
        ]
        
        print(f"Разбито на {num_batches} пакетов по {batch_size} файлов")
        
        # Используем больше потоков для параллельного удаления
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Запускаем удаление пакетов параллельно
            list(executor.map(delete_resources_batch, resource_batches))
        
        end_time = time.time()
        print(f"\nВсе фотографии успешно удалены!")
        print(f"Общее время выполнения: {end_time - start_time:.2f} секунд")
        
    except Exception as e:
        print(f"Произошла ошибка: {e}")

if __name__ == "__main__":
    delete_all_resources() 