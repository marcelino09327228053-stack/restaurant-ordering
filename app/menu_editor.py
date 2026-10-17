"""Validated Menu Editor settings and shared upload checks."""
import io
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, field_validator
from fastapi import HTTPException
from PIL import Image

class MenuAppearance(BaseModel):
    background: str = '#0b0b0d'
    text: str = '#f5f5f4'
    category: str = '#a8a8ad'
    description: str = '#a8a8ad'
    card: str = '#17171b'
    price: str = '#f97316'
    font: Literal['Arial', 'Roboto', 'Poppins', 'Montserrat', 'Open Sans', 'Lato', 'Nunito', 'Oswald', 'Merriweather', 'Playfair Display'] = 'Arial'
    currency: Literal['PHP', 'USD', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'SGD'] = 'PHP'
    gradient: bool = False
    gradient_color: str = '#6d28ff'
    background_image: str = ''
    glow: bool = False
    intensity: Literal['low', 'medium', 'high'] = 'medium'
    media_url: str = ''
    media_type: Literal['image', 'video', 'none'] = 'none'

    @field_validator('background', 'text', 'category', 'description', 'card', 'price', 'gradient_color')
    @classmethod
    def color(cls, value):
        import re
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', value):
            raise ValueError('Use a six-digit hex color.')
        return value

    @field_validator('media_url', 'background_image')
    @classmethod
    def media_reference(cls, value):
        if not value:
            return value
        if len(value) > 2000 or any(c in value for c in '\r\n'):
            raise ValueError('Invalid media reference.')
        parsed = urlparse(value)
        if not (value.startswith('/static/uploads/') or (parsed.scheme == 'https' and parsed.netloc)):
            raise ValueError('Use an uploaded media reference or HTTPS URL.')
        return value

def validate_menu_upload(raw, content_type):
    if content_type.startswith('image/'):
        try:
            with Image.open(io.BytesIO(raw)) as image:
                expected = {'image/jpeg':'JPEG','image/png':'PNG','image/webp':'WEBP','image/gif':'GIF'}
                if image.format != expected.get(content_type):
                    raise ValueError('Image content does not match its format.')
                image.verify()
        except Exception as exc:
            raise HTTPException(400, 'Invalid or damaged image.') from exc
    elif content_type == 'video/mp4':
        if len(raw) < 16 or raw[4:8] != b'ftyp':
            raise HTTPException(400, 'Invalid MP4 file.')
    elif content_type == 'video/webm':
        if not raw.startswith(b'\x1a\x45\xdf\xa3'):
            raise HTTPException(400, 'Invalid WebM file.')
    else:
        raise HTTPException(400, 'Use JPEG, PNG, WebP, GIF, MP4 or WebM.')
