"""
Unit tests for ImageLoader
"""

import pytest
import numpy as np
from pathlib import Path
from PIL import Image
import tempfile
import os

from core.image_loader import ImageLoader


class TestImageLoader:
    """Test suite for ImageLoader class"""
    
    @pytest.fixture
    def loader(self):
        """Create ImageLoader instance"""
        return ImageLoader()
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image"""
        # Create a simple test image
        img = Image.new('RGB', (1000, 1000), color='red')
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_load_valid_image(self, loader, sample_image):
        """Test loading a valid image"""
        result = loader.load(sample_image)
        
        assert result is not None
        assert 'image' in result
        assert 'original_size' in result
        assert 'dpi' in result
        assert isinstance(result['image'], np.ndarray)
        assert result['original_size'] == (1000, 1000)
    
    def test_load_nonexistent_file(self, loader):
        """Test loading non-existent file"""
        with pytest.raises(FileNotFoundError):
            loader.load('nonexistent.jpg')
    
    def test_load_invalid_format(self, loader):
        """Test loading invalid format"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.txt', delete=False)
        temp_file.write(b'not an image')
        temp_file.close()
        
        try:
            with pytest.raises(ValueError):
                loader.load(temp_file.name)
        finally:
            os.unlink(temp_file.name)
    
    def test_upscaling(self, loader, sample_image):
        """Test image upscaling"""
        result = loader.load(sample_image, target_dpi=600)
        
        # Should be upscaled
        assert result['upscaled'] == True
        assert result['dpi'] == 600
        
        # Size should be doubled (72 DPI to 600 DPI ≈ 8x)
        assert result['original_size'][0] > 1000
    
    def test_validate_size_pass(self, loader, sample_image):
        """Test size validation - pass"""
        image_data = loader.load(sample_image)
        valid, message = loader.validate_size(image_data)
        
        assert valid == True
        assert message == "OK"
    
    def test_validate_size_fail(self, loader):
        """Test size validation - fail"""
        # Create tiny image
        img = Image.new('RGB', (100, 100), color='blue')
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        img.save(temp_file.name)
        temp_file.close()
        
        try:
            image_data = loader.load(temp_file.name)
            valid, message = loader.validate_size(image_data, min_width=500, min_height=500)
            
            assert valid == False
            assert "too small" in message.lower()
        finally:
            os.unlink(temp_file.name)
