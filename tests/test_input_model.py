import pytest
from src.input_model import OpenaiVectorStoreIntegration
from pydantic import ConfigDict

class ActorInput(OpenaiVectorStoreIntegration):
    model_config = ConfigDict(str_strip_whitespace=True)


def test_input_model_whitespace_removal():
    """Test that input model automatically strips whitespace."""
    
    test_data = {
        "vectorStoreId": "  vs_123  ",
        "openaiApiKey": "sk-1234567890abcdef",
        "datasetFields": ["url", "text"],
    }
    
    model = ActorInput(**test_data)
    
    assert model.vectorStoreId == "vs_123"
    assert model.openaiApiKey == "sk-1234567890abcdef"
    assert model.datasetFields == ["url", "text"]
