from django.db import connection
from django.http import JsonResponse


def health_check(request):
    """Simple health check endpoint for Docker/load balancer probes."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "healthy", "db": "ok"})
    except Exception as e:
        return JsonResponse(
            {"status": "unhealthy", "db": str(e)}, status=503
        )
