import os
import uuid
from PIL import Image
from werkzeug.datastructures import FileStorage
from flask import current_app

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}


def validate_and_save_image(file: FileStorage, subfolder: str = '') -> tuple[bool, str]:
    """
    Strict validation of uploaded images:
    1. Check presence and extension
    2. Check MIME type
    3. Check byte signature with Pillow
    4. Save with random UUID filename
    Returns (success: bool, filename_or_error_message: str)
    """
    if not file or not file.filename:
        return False, "No file uploaded."

    filename = file.filename.strip()
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File format .{ext} is not allowed. Supported formats: JPG, PNG, WEBP."

    # Validate MIME type from browser header
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        return False, "Invalid image MIME type."

    # Check file size (in memory/stream check)
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 5 * 1024 * 1024)
    if size > max_size:
        return False, f"File size exceeds maximum allowed size of {max_size // (1024 * 1024)}MB."

    # Verify actual image content using Pillow
    try:
        img = Image.open(file.stream)
        img.verify()
        if img.format not in ALLOWED_IMAGE_FORMATS:
            return False, f"Invalid or corrupted image format: {img.format}."
    except Exception as e:
        return False, f"Image verification failed: File is not a valid image."
    finally:
        file.seek(0)

    # Generate safe random UUID filename
    safe_filename = f"{uuid.uuid4().hex}.{ext}"

    # Check if Cloudinary is configured (for persistent cloud storage on Render)
    cloudinary_url = os.getenv('CLOUDINARY_URL')
    cloudinary_cloud = os.getenv('CLOUDINARY_CLOUD_NAME')
    if cloudinary_url or cloudinary_cloud:
        try:
            import cloudinary
            import cloudinary.uploader
            res = cloudinary.uploader.upload(
                file,
                folder=f"campusconnect/{subfolder}" if subfolder else "campusconnect",
                resource_type="image"
            )
            secure_url = res.get('secure_url')
            if secure_url:
                return True, secure_url
        except Exception as e:
            current_app.logger.warning(f"Cloudinary upload failed: {e}; falling back to local filesystem storage.")
            file.seek(0)

    target_dir = current_app.config['UPLOAD_FOLDER']
    if subfolder:
        target_dir = os.path.join(target_dir, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    dest_path = os.path.join(target_dir, safe_filename)
    file.save(dest_path)

    return True, safe_filename
