from django.db import connection
from django.http import JsonResponse


def health(request):
    """Sonde de vivacité : 200 + un aller-retour DB trivial.

    Publique (pas d'auth) : consommée par les healthchecks Docker et un
    éventuel monitoring externe. Une base injoignable lève → 500, ce qui
    est exactement le signal attendu.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        cursor.fetchone()
    return JsonResponse({"status": "ok"})
