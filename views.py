from .semantic_search import SemanticSearch
import os

# Инициализируем поиск при запуске сервера
semantic_search = SemanticSearch(os.path.join(os.path.dirname(__file__), 'image_data.db'))

@csrf_exempt
def semantic_search_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query', '')
            top_k = int(data.get('top_k', 10))
            
            results = semantic_search.search(query, top_k)
            return JsonResponse({'results': results})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405) 