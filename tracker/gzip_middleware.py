import gzip
from django.utils.deprecation import MiddlewareMixin

class GZipMiddleware(MiddlewareMixin):
    def process_request(self, request):
        encoding = request.META.get('HTTP_CONTENT_ENCODING', '')
        if 'gzip' in encoding:
            try:
                request._body = gzip.decompress(request.body)
            except Exception as e:
                print(f"GZip Decompression Failed: {e}")
                # Let it fail downstream or handle error
