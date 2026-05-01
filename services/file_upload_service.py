import os
import uuid
from werkzeug.utils import secure_filename

class FileUploadService:
    """Handles file upload operations"""
    
    def __init__(self):
        # Upload directory is relative to project root
        self.upload_base = 'static/uploads'
    
    def save_file(self, file, subfolder='documents'):
        """Save uploaded file and return its path"""
        if not file or not file.filename:
            return None
        
        # Secure the filename
        filename = secure_filename(file.filename)
        if not filename:
            return None
        
        # Generate unique filename to avoid collisions
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Create full path
        subfolder_path = os.path.join(self.upload_base, subfolder)
        full_path = os.path.join(subfolder_path, unique_filename)
        
        # Ensure directory exists
        os.makedirs(subfolder_path, exist_ok=True)
        
        # Save file
        try:
            file.save(full_path)
            return full_path
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    def delete_file(self, file_path):
        """Delete uploaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            print(f"Error deleting file: {e}")
        return False
    
    def get_public_url(self, file_path):
        """Get public URL for uploaded file"""
        return file_path
