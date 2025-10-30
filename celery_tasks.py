from celery import Celery
import redis
import json
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
import whisper
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Celery应用
celery_app = Celery(
    'video_to_text',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    task_soft_time_limit=3300,  # 55分钟软超时
)

# Redis客户端
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

# Whisper模型缓存
whisper_models = {}

def update_task_status(task_id: str, status: str, progress: str = None, 
                       result: dict = None, error: str = None):
    """更新任务状态到Redis"""
    try:
        task_data_str = redis_client.get(f'task:{task_id}')
        if task_data_str:
            task_data = json.loads(task_data_str)
            task_data['status'] = status
            task_data['updated_at'] = datetime.utcnow().isoformat()
            
            if progress:
                task_data['progress'] = progress
            if result:
                task_data['result'] = result
            if error:
                task_data['error'] = error
            
            redis_client.setex(
                f'task:{task_id}',
                3600 * 24,
                json.dumps(task_data)
            )
    except Exception as e:
        logger.error(f'更新任务状态失败: {str(e)}')

def download_video_audio(video_url: str, output_path: str) -> str:
    """使用yt-dlp下载视频音频"""
    try:
        # 直接下载音频，跳过视频
        cmd = [
            'yt-dlp',
            '-x',  # 只提取音频
            '--audio-format', 'wav',
            '--audio-quality', '0',  # 最佳质量
            '-o', output_path,
            '--no-playlist',  # 不下载播放列表
            '--max-filesize', '500M',  # 限制文件大小
            video_url
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时
        )
        
        if result.returncode != 0:
            raise Exception(f'yt-dlp下载失败: {result.stderr}')
        
        # 查找实际生成的文件
        base_path = output_path.rsplit('.', 1)[0]
        if os.path.exists(f'{base_path}.wav'):
            return f'{base_path}.wav'
        elif os.path.exists(output_path):
            return output_path
        else:
            raise Exception('下载的音频文件未找到')
            
    except subprocess.TimeoutExpired:
        raise Exception('视频下载超时')
    except Exception as e:
        raise Exception(f'下载失败: {str(e)}')

def process_audio_with_ffmpeg(input_path: str, output_path: str) -> str:
    """使用FFmpeg处理音频，转换为Whisper最佳格式"""
    try:
        # 转换为单声道、16kHz采样率的WAV
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vn',  # 不处理视频
            '-acodec', 'pcm_s16le',  # PCM编码
            '-ac', '1',  # 单声道
            '-ar', '16000',  # 16kHz采样率
            '-y',  # 覆盖输出文件
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode != 0:
            raise Exception(f'FFmpeg处理失败: {result.stderr}')
        
        return output_path
        
    except subprocess.TimeoutExpired:
        raise Exception('音频处理超时')
    except Exception as e:
        raise Exception(f'音频处理失败: {str(e)}')

def transcribe_with_whisper(audio_path: str, model_size: str = 'small', 
                            language: str = None, output_format: str = 'txt') -> dict:
    """使用Whisper转录音频"""
    try:
        # 加载或使用缓存的模型
        if model_size not in whisper_models:
            logger.info(f'加载Whisper模型: {model_size}')
            whisper_models[model_size] = whisper.load_model(model_size)
        
        model = whisper_models[model_size]
        
        # 转录参数
        transcribe_options = {
            'fp16': False,  # 禁用FP16（CPU兼容）
            'verbose': False
        }
        
        if language:
            transcribe_options['language'] = language
        
        logger.info('开始转录音频...')
        result = model.transcribe(audio_path, **transcribe_options)
        
        # 处理输出格式
        if output_format == 'txt':
            return {
                'format': 'txt',
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'duration': result.get('duration', 0)
            }
        elif output_format == 'srt':
            # 生成SRT字幕格式
            srt_content = generate_srt(result['segments'])
            return {
                'format': 'srt',
                'text': result['text'].strip(),
                'srt': srt_content,
                'language': result.get('language', 'unknown'),
                'duration': result.get('duration', 0),
                'segments_count': len(result['segments'])
            }
        
    except Exception as e:
        raise Exception(f'语音识别失败: {str(e)}')

def generate_srt(segments: list) -> str:
    """生成SRT字幕格式"""
    srt_lines = []
    for i, segment in enumerate(segments, 1):
        start = format_timestamp(segment['start'])
        end = format_timestamp(segment['end'])
        text = segment['text'].strip()
        
        srt_lines.append(f"{i}")
        srt_lines.append(f"{start} --> {end}")
        srt_lines.append(text)
        srt_lines.append("")  # 空行
    
    return '\n'.join(srt_lines)

def format_timestamp(seconds: float) -> str:
    """将秒数转换为SRT时间戳格式 (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

@celery_app.task(bind=True, name='process_video_task')
def process_video_task(self, task_id: str, video_url: str, output_format: str,
                       language: str = None, model_size: str = 'small'):
    """
    处理视频转文字的完整流程
    """
    temp_dir = None
    
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix='video_to_text_')
        logger.info(f'任务 {task_id} 开始处理: {video_url}')
        
        # 步骤1: 下载视频音频
        update_task_status(task_id, 'processing', '正在下载视频...')
        audio_raw_path = os.path.join(temp_dir, 'audio_raw.wav')
        downloaded_audio = download_video_audio(video_url, audio_raw_path)
        logger.info(f'音频下载完成: {downloaded_audio}')
        
        # 步骤2: 处理音频格式
        update_task_status(task_id, 'processing', '正在处理音频格式...')
        audio_processed_path = os.path.join(temp_dir, 'audio_processed.wav')
        processed_audio = process_audio_with_ffmpeg(downloaded_audio, audio_processed_path)
        logger.info(f'音频处理完成: {processed_audio}')
        
        # 步骤3: 语音识别
        update_task_status(task_id, 'processing', f'正在使用Whisper({model_size})进行语音识别...')
        transcription_result = transcribe_with_whisper(
            processed_audio,
            model_size=model_size,
            language=language,
            output_format=output_format
        )
        logger.info(f'语音识别完成')
        
        # 更新任务为完成状态
        update_task_status(
            task_id,
            'completed',
            '处理完成',
            result=transcription_result
        )
        
        logger.info(f'任务 {task_id} 处理完成')
        return transcription_result
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f'任务 {task_id} 处理失败: {error_msg}')
        update_task_status(task_id, 'failed', error=error_msg)
        raise
        
    finally:
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f'临时目录已清理: {temp_dir}')
            except Exception as e:
                logger.error(f'清理临时目录失败: {str(e)}')