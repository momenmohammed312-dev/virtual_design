"""
Unit tests for StrokeValidator
"""

import pytest
import numpy as np
import cv2

from core.stroke_validator import StrokeValidator


class TestStrokeValidator:
    """Test suite for StrokeValidator class"""
    
    @pytest.fixture
    def validator(self):
        """Create StrokeValidator instance"""
        return StrokeValidator(min_stroke_mm=0.5, dpi=300)
    
    @pytest.fixture
    def thick_mask(self):
        """Create mask with thick strokes"""
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        cv2.rectangle(mask, (100, 100), (900, 900), 255, 50)  # Thick rectangle
        return mask
    
    @pytest.fixture
    def thin_mask(self):
        """Create mask with thin strokes"""
        mask = np.zeros((1000, 1000), dtype=np.uint8)
        cv2.rectangle(mask, (100, 100), (900, 900), 255, 2)  # Thin rectangle
        return mask
    
    def test_mm_to_pixels(self, validator):
        """Test mm to pixels conversion"""
        pixels = validator._mm_to_pixels(0.5)
        
        # 0.5mm at 300 DPI should be about 6 pixels
        assert pixels == 6
    
    def test_pixels_to_mm(self, validator):
        """Test pixels to mm conversion"""
        mm = validator._pixels_to_mm(6)
        
        # 6 pixels at 300 DPI should be about 0.5mm
        assert mm == pytest.approx(0.5, abs=0.1)
    
    def test_validate_thick_mask(self, validator, thick_mask):
        """Test validation of thick strokes"""
        result = validator.validate_mask(thick_mask)
        
        assert result['valid'] == True
        assert result['violations'] == 0
        assert len(result['warnings']) == 0
    
    def test_validate_thin_mask(self, validator, thin_mask):
        """Test validation of thin strokes"""
        result = validator.validate_mask(thin_mask)
        
        assert result['valid'] == False
        assert result['violations'] > 0
        assert len(result['warnings']) > 0
    
    def test_thicken_strokes(self, validator, thin_mask):
        """Test stroke thickening"""
        thickened = validator.thicken_strokes(thin_mask, target_width_mm=0.5)
        
        # Validate thickened result
        result = validator.validate_mask(thickened)
        
        # Should pass validation now
        assert result['min_width_mm'] >= 0.4  # Allow small margin
