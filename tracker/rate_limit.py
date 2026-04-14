"""
Simple IP-based rate limiter using Django's cache framework.
No external dependencies required.

Usage:
    @rate_limit(requests=5, window=60)   # 5 requests per 60 seconds
    def my_view(request): ...
"""
import functools
from django.core.cache import cache
from django.http import JsonResponse


def _get_client_ip(request):
    """Extract real client IP, respecting X-Forwarded-For."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def rate_limit(requests: int, window: int, key_prefix: str = ''):
    """
    Decorator that limits a view to `requests` calls per `window` seconds per IP.

    Args:
        requests: max number of allowed requests in the window
        window:   time window in seconds
        key_prefix: optional string to namespace the cache key
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            ip = _get_client_ip(request)
            prefix = key_prefix or view_func.__name__
            cache_key = f'rl:{prefix}:{ip}'

            count = cache.get(cache_key, 0)

            if count >= requests:
                return JsonResponse(
                    {
                        'error': 'Too many requests. Please try again later.',
                        'retry_after': window,
                    },
                    status=429,
                )

            # Increment — set with timeout only on first hit
            if count == 0:
                cache.set(cache_key, 1, timeout=window)
            else:
                cache.set(cache_key, count + 1, timeout=window)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
