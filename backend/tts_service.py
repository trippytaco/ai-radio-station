"""
Text-to-Speech Service
Supports Google Cloud TTS and ElevenLabs
"""

import os
import asyncio
from abc import ABC, abstractmethod
from typing import Optional
import io

try:
    from google.cloud import texttospeech
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from elevenlabs import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False


class TTSProvider(ABC):
    """Abstract base class for TTS providers"""
    
    @abstractmethod
    async def synthesize(self, text: str, voice_id: str) -> bytes:
        """Synthesize text to speech and return audio bytes"""
        pass


class GoogleCloudTTS(TTSProvider):
    """Google Cloud Text-to-Speech provider"""
    
    def __init__(self):
        if not GOOGLE_AVAILABLE:
            raise RuntimeError("Google Cloud TTS not installed. Install with: pip install google-cloud-texttospeech")
        
        credentials_path = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
        if not credentials_path:
            raise RuntimeError("GOOGLE_CLOUD_CREDENTIALS_JSON not set in environment")
        
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        self.client = texttospeech.TextToSpeechClient()
        
        # Voice mappings
        self.voices = {
            "alex_female": "en-US-Neural2-C",      # Female, energetic
            "jordan_male": "en-US-Neural2-A",      # Male, smooth
            "default": "en-US-Neural2-C"
        }
    
    async def synthesize(self, text: str, voice_id: str = "alex_female") -> bytes:
        """Synthesize text using Google Cloud TTS"""
        try:
            voice_name = self.voices.get(voice_id, self.voices["default"])
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=1.0,
                pitch=0.0
            )
            
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )
            
            return response.audio_content
        
        except Exception as e:
            raise RuntimeError(f"Google Cloud TTS error: {str(e)}")


class ElevenLabsTTS(TTSProvider):
    """ElevenLabs Text-to-Speech provider"""
    
    def __init__(self):
        if not ELEVENLABS_AVAILABLE:
            raise RuntimeError("ElevenLabs not installed. Install with: pip install elevenlabs")
        
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY not set in environment")
        
        self.client = ElevenLabs(api_key=api_key)
        
        # Voice IDs (free tier available)
        self.voices = {
            "alex_female": "EXAVITQu4vr4xnSDxMHj",  # Bella - sassy
            "jordan_male": "pMsXgVXv3BLzUAu6UVCH",   # Josh - smooth
            "default": "EXAVITQu4vr4xnSDxMHj"
        }
    
    async def synthesize(self, text: str, voice_id: str = "alex_female") -> bytes:
        """Synthesize text using ElevenLabs TTS"""
        try:
            voice = self.voices.get(voice_id, self.voices["default"])
            
            audio = self.client.text_to_speech.convert(
                voice_id=voice,
                text=text,
                model_id="eleven_multilingual_v2"
            )

            # Convert generator to bytes
            audio_bytes = b"".join(audio)
            return audio_bytes
        
        except Exception as e:
            raise RuntimeError(f"ElevenLabs TTS error: {str(e)}")


class TTSFactory:
    """Factory for creating TTS provider instances"""
    
    _providers = {}
    
    @staticmethod
    def get_provider(provider_name: str = None) -> TTSProvider:
        """Get TTS provider instance"""
        if provider_name is None:
            provider_name = os.getenv("TTS_PROVIDER", "google").lower()
        
        if provider_name in TTSFactory._providers:
            return TTSFactory._providers[provider_name]
        
        try:
            if provider_name == "google":
                provider = GoogleCloudTTS()
            elif provider_name == "elevenlabs":
                provider = ElevenLabsTTS()
            else:
                raise ValueError(f"Unknown TTS provider: {provider_name}")
            
            TTSFactory._providers[provider_name] = provider
            return provider
        
        except Exception as e:
            raise RuntimeError(f"Failed to initialize TTS provider '{provider_name}': {str(e)}")


# Global instance
_tts_provider: Optional[TTSProvider] = None


def get_tts_provider() -> TTSProvider:
    """Get or create global TTS provider"""
    global _tts_provider
    if _tts_provider is None:
        _tts_provider = TTSFactory.get_provider()
    return _tts_provider


def set_provider(provider_name: str) -> TTSProvider:
    """Switch the global TTS provider to a new one, replacing the cached instance"""
    global _tts_provider
    _tts_provider = TTSFactory.get_provider(provider_name)
    return _tts_provider


async def synthesize_text(text: str, voice_id: str = "alex_female") -> bytes:
    """Convenience function to synthesize text"""
    provider = get_tts_provider()
    return await provider.synthesize(text, voice_id)
