import os
import ast
import tempfile
import zipfile

def extract_routes_from_urls(urls_file_path):
    routes = []
    
    try:
        with open(urls_file_path, 'r', encoding='utf-8') as file:
            tree = ast.parse(file.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'path':
                    if len(node.args) >= 2:
                        route_str = ""
                        if isinstance(node.args[0], ast.Constant):
                            route_str = node.args[0].value
                        
                        view_name = ""
                        if isinstance(node.args[1], ast.Attribute):
                            view_name = node.args[1].attr 
                        elif isinstance(node.args[1], ast.Name):
                            view_name = node.args[1].id
                        elif isinstance(node.args[1], ast.Call) and isinstance(node.args[1].func, ast.Attribute):
                            # Handle class-based views like MyView.as_view()
                            view_name = node.args[1].func.value.id if isinstance(node.args[1].func.value, ast.Name) else ""
                            
                        if route_str and view_name:
                            routes.append({
                                'route': f"/{route_str}".replace('//', '/'),
                                'view_name': view_name
                            })
                elif isinstance(node.func, ast.Attribute) and node.func.attr == 'register':
                    if len(node.args) >= 2:
                        route_str = ""
                        if isinstance(node.args[0], ast.Constant):
                            route_str = node.args[0].value
                            
                        view_name = ""
                        if isinstance(node.args[1], ast.Name):
                            view_name = node.args[1].id
                            
                        if route_str and view_name:
                            routes.append({
                                'route': f"/{route_str}".replace('//', '/'),
                                'view_name': view_name
                            })
    except Exception as e:
        print(f"Error parsing urls.py at {urls_file_path}: {e}")
    return routes

def extract_inline_comments(lines, start_line, end_line):
    comments = []
    # AST lineno is 1-indexed; convert to 0-indexed for the list
    for i in range(start_line - 1, end_line):
        line = lines[i].strip()
        if line.startswith('#'):
            # Keep only the comment text
            comments.append(line.lstrip('#').strip())
    return " ".join(comments) if comments else ""

def extract_view_details(views_file_path, target_view_name):
    try:
        with open(views_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            tree = ast.parse(content)
            lines = content.splitlines()

        for node in ast.walk(tree):
            # Function-based views
            if isinstance(node, ast.FunctionDef):
                if node.name == target_view_name:
                    docstring = ast.get_docstring(node) or ""
                    start_line = node.lineno
                    end_line = getattr(node, 'end_lineno', start_line)
                    inline_comments = extract_inline_comments(lines, start_line, end_line)
                    
                    description = f"{docstring}\n{inline_comments}".strip() if docstring else inline_comments
                    if not description:
                        description = "لا يوجد وصف متاح."
                        
                    methods = ['GET'] # Default
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call) and getattr(decorator.func, 'id', '') == 'api_view':
                            if decorator.args and isinstance(decorator.args[0], ast.List):
                                methods = [elt.value for elt in decorator.args[0].elts if isinstance(elt, ast.Constant)]
                    return {'methods': methods, 'description': description, 'type': 'function'}

            # Class-based views
            elif isinstance(node, ast.ClassDef):
                if node.name == target_view_name:
                    docstring = ast.get_docstring(node) or ""
                    start_line = node.lineno
                    end_line = getattr(node, 'end_lineno', start_line)
                    inline_comments = extract_inline_comments(lines, start_line, end_line)
                    
                    description = f"{docstring}\n{inline_comments}".strip() if docstring else inline_comments
                    if not description:
                        description = "لا يوجد وصف متاح."
                        
                    methods = []
                    # Check for explicit method handlers
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and item.name in ['get', 'post', 'put', 'patch', 'delete']:
                            methods.append(item.name.upper())

                    if not methods:
                        # Probably a ViewSet or something generic, fallback
                        methods = ['GET', 'POST', 'PUT', 'DELETE']
                    return {'methods': methods, 'description': description, 'type': 'class'}

    except Exception as e:
        print(f"Error parsing views.py at {views_file_path}: {e}")
    return None

def find_app_pairs(base_dir):
    """Finds directories that contain both urls.py and views.py"""
    pairs = []
    for root, dirs, files in os.walk(base_dir):
        if 'urls.py' in files and 'views.py' in files:
            pairs.append({
                'urls': os.path.join(root, 'urls.py'),
                'views': os.path.join(root, 'views.py'),
                'app_name': os.path.basename(root)
            })
    return pairs

def analyze_django_zip(zip_file_path):
    """
    Extracts a zip file, analyzes all app directories containing urls/views,
    and returns a formatted list of API endpoints.
    """
    final_apis = []
    temp_dir = tempfile.mkdtemp()
    
    print(f"DEBUG: Processing ZIP file: {zip_file_path}")
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        print(f"DEBUG: ZIP extracted to {temp_dir}")
        app_pairs = find_app_pairs(temp_dir)
        print(f"DEBUG: Found app pairs: {app_pairs}")
        
        for pair in app_pairs:
            print(f"DEBUG: Analyzing pair {pair['app_name']}")
            routes = extract_routes_from_urls(pair['urls'])
            print(f"DEBUG: Extracted routes: {routes}")
            for route_info in routes:
                view_details = extract_view_details(pair['views'], route_info['view_name'])
                print(f"DEBUG: View details for {route_info['view_name']}: {view_details}")
                if view_details:
                    app_prefix = f"/{pair['app_name']}" if pair['app_name'] else ""
                    # A naive prefix matching since exact django URL inclusion involves parsing project-level urls.py
                    # which is complex. We'll pre-fix with app name if we want, but let's just use the extracted route.
                    for method in view_details['methods']:
                        final_apis.append({
                            'app': pair['app_name'],
                            'path': route_info['route'],
                            'method': method,
                            'description': view_details['description']
                        })
    except Exception as e:
        print(f"Error analyzing zip: {e}")
    finally:
        # Cleanup temp directory (ideally using shutil, but let's keep it simple or handled elsewhere if we wanted)
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except:
            pass
            
    print(f"DEBUG: Final extracted APIs: {final_apis}")
    return final_apis
