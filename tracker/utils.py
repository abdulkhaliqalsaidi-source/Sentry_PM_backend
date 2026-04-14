import hashlib

def generate_hash(error_type, error_location, project_name=""):
    """
    Generates a unique hash for an error based on its type, location, and project.
    This ensures that similar errors in different projects are isolated.
    """
    # Combine type, location, and project to prevent cross-project collisions
    signature = f"{error_type}-{error_location}-{project_name}"
    return hashlib.md5(signature.encode('utf-8')).hexdigest()
