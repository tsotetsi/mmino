"""
Audio processing module using FFmpeg
"""
import subprocess
import os
import json
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import shutil

class ProcessingError(Exception):
    """Custom exception for audio processing errors"""
    pass

class AudioProcessor:
    """Handle audio processing operations using FFmpeg"""
    
    def __init__(self, input_path: str):
        if not os.path.exists(input_path):
            raise ProcessingError(f"Input file not found: {input_path}")
        
        self.input_path = input_path
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"
        
        # Validate FFmpeg is available
        try:
            subprocess.run([self.ffmpeg_path, "-version"], 
                          capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise ProcessingError("FFmpeg is not installed or not in PATH")
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get audio metadata using ffprobe"""
        cmd = [
            self.ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            self.input_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract audio stream info
            audio_stream = next(
                (s for s in data.get('streams', []) if s.get('codec_type') == 'audio'),
                {}
            )
            
            format_info = data.get('format', {})
            
            return {
                'duration': float(format_info.get('duration', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)) // 1000 if format_info.get('bit_rate') else None,
                'sample_rate': int(audio_stream.get('sample_rate', 0)) if audio_stream.get('sample_rate') else None,
                'channels': int(audio_stream.get('channels', 0)) if audio_stream.get('channels') else None,
                'codec': audio_stream.get('codec_name'),
                'format': format_info.get('format_name'),
                'file_size': int(format_info.get('size', 0))
            }
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError) as e:
            raise ProcessingError(f"Failed to extract metadata: {e}")
    
    def convert(self, format: str = "mp3", bitrate: int = 192, 
                samplerate: int = 44100, channels: int = 2) -> str:
        """Convert audio to different format"""
        # Validate parameters
        allowed_formats = ['mp3', 'wav', 'flac', 'ogg', 'm4a', 'aac']
        if format.lower() not in allowed_formats:
            raise ProcessingError(f"Unsupported format: {format}. Allowed: {allowed_formats}")
        
        if bitrate < 64 or bitrate > 320:
            raise ProcessingError(f"Bitrate {bitrate}kbps is out of range (64-320)")
        
        # Generate output path
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_converted.{format}"
        
        # Build FFmpeg command
        cmd = [
            self.ffmpeg_path,
            '-i', self.input_path,
            '-b:a', f'{bitrate}k',
            '-ar', str(samplerate),
            '-ac', str(channels),
            '-y',  # Overwrite output
        ]
        
        # Add format-specific options
        if format == 'mp3':
            cmd.extend(['-codec:a', 'libmp3lame', '-q:a', '2'])
        elif format == 'flac':
            cmd.extend(['-codec:a', 'flac', '-compression_level', '8'])
        elif format == 'wav':
            cmd.extend(['-codec:a', 'pcm_s16le'])
        
        cmd.append(output_path)
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise ProcessingError(f"Conversion failed: {e.stderr}")
    
    def trim(self, start: float, duration: Optional[float] = None, 
             end: Optional[float] = None) -> str:
        """Trim audio file"""
        if start < 0:
            raise ProcessingError("Start time cannot be negative")
        
        if duration is not None and duration <= 0:
            raise ProcessingError("Duration must be positive")
        
        if end is not None and end <= start:
            raise ProcessingError("End time must be greater than start time")
        
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_trimmed{os.path.splitext(self.input_path)[1]}"
        
        cmd = [self.ffmpeg_path, '-i', self.input_path, '-ss', str(start)]
        
        if duration:
            cmd.extend(['-t', str(duration)])
        elif end:
            cmd.extend(['-to', str(end)])
        
        cmd.extend(['-c', 'copy', '-y', output_path])
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            # Try with re-encoding if copy fails
            cmd = [self.ffmpeg_path, '-i', self.input_path, '-ss', str(start)]
            if duration:
                cmd.extend(['-t', str(duration)])
            elif end:
                cmd.extend(['-to', str(end)])
            cmd.extend(['-y', output_path])
            
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                return output_path
            except subprocess.CalledProcessError as e2:
                raise ProcessingError(f"Trim failed: {e2.stderr}")
    
    def normalize(self, target: float = -16.0, peak: float = -1.0, 
                  loudness_range: int = 11) -> str:
        """Normalize audio loudness using EBU R128"""
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_normalized{os.path.splitext(self.input_path)[1]}"
        
        cmd = [
            self.ffmpeg_path, '-i', self.input_path,
            '-filter:a', f'loudnorm=I={target}:TP={peak}:LRA={loudness_range}:print_format=json',
            '-f', 'null', '-'
        ]
        
        try:
            # First pass to get analysis
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Extract loudnorm stats from output (simplified)
            # In production, you'd parse the JSON from stderr
            
            # Second pass to apply normalization
            cmd = [
                self.ffmpeg_path, '-i', self.input_path,
                '-filter:a', f'loudnorm=I={target}:TP={peak}:LRA={loudness_range}',
                '-y', output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
            
        except subprocess.CalledProcessError as e:
            raise ProcessingError(f"Normalization failed: {e.stderr}")
    
    def extract_audio(self, format: str = "mp3") -> str:
        """Extract audio from video file"""
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_audio.{format}"
        
        cmd = [
            self.ffmpeg_path, '-i', self.input_path,
            '-vn',  # No video
            '-acodec', 'libmp3lame' if format == 'mp3' else 'copy',
            '-y', output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise ProcessingError(f"Audio extraction failed: {e.stderr}")
    
    def compress(self, threshold: float = -20.0, ratio: float = 4.0,
                 attack: int = 5, release: int = 50) -> str:
        """Apply audio compression"""
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_compressed{os.path.splitext(self.input_path)[1]}"
        
        cmd = [
            self.ffmpeg_path, '-i', self.input_path,
            '-filter:a', f'acompressor=threshold={threshold}dB:ratio={ratio}:attack={attack}:release={release}',
            '-y', output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise ProcessingError(f"Compression failed: {e.stderr}")
    
    def generate_spectrogram(self, width: int = 1024, height: int = 512,
                            colormap: str = "viridis", db_range: int = 80) -> str:
        """Generate spectrogram image"""
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_spectrogram.png"
        
        cmd = [
            self.ffmpeg_path, '-i', self.input_path,
            '-lavfi', f'showspectrumpic=s={width}x{height}:mode=combined:color={colormap}:scale=log:fscale=log:gain=20:legend=1',
            '-y', output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise ProcessingError(f"Spectrogram generation failed: {e.stderr}")
    
    def merge(self, other_file: str, output_format: str = "mp3") -> str:
        """Merge two audio files"""
        if not os.path.exists(other_file):
            raise ProcessingError(f"Second file not found: {other_file}")
        
        # Create a temporary file list
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"file '{os.path.abspath(self.input_path)}'\n")
            f.write(f"file '{os.path.abspath(other_file)}'\n")
            filelist_path = f.name
        
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_merged.{output_format}"
        
        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', filelist_path,
            '-c', 'copy',
            '-y', output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            # Try with re-encoding
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', filelist_path,
                '-y', output_path
            ]
            try:
                subprocess.run(cmd, capture_output=True, check=True)
                return output_path
            except subprocess.CalledProcessError as e2:
                raise ProcessingError(f"Merge failed: {e2.stderr}")
        finally:
            os.unlink(filelist_path)
    
    def add_effects(self, effects: Dict[str, Any]) -> str:
        """Add audio effects"""
        base_name = os.path.splitext(self.input_path)[0]
        output_path = f"{base_name}_effects{os.path.splitext(self.input_path)[1]}"
        
        # Build filter chain
        filters = []
        
        if effects.get('reverb'):
            filters.append(f'aecho=0.8:0.9:{effects["reverb"]["delay"]}:{effects["reverb"]["decay"]}')
        
        if effects.get('equalizer'):
            eq = effects['equalizer']
            filters.append(f'equalizer=f={eq["frequency"]}:t={eq["type"]}:width={eq["width"]}:g={eq["gain"]}')
        
        if effects.get('chorus'):
            chorus = effects['chorus']
            filters.append(f'chorus=0.5:0.9:{chorus["delay"]}:0.4:{chorus["depth"]}:{chorus["speed"]}')
        
        if not filters:
            raise ProcessingError("No effects specified")
        
        filter_chain = ','.join(filters)
        
        cmd = [
            self.ffmpeg_path, '-i', self.input_path,
            '-filter:a', filter_chain,
            '-y', output_path
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            raise ProcessingError(f"Effects processing failed: {e.stderr}")