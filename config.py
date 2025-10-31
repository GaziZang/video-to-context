"""
配置管理模块
集中管理所有配置项，支持环境变量覆盖
"""

import os
from typing import Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """应用配置"""
    
    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "视频转文字API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Redis配置
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    
    # 任务配置
    TASK_TIME_LIMIT: int = 3600  # 1小时
    TASK_SOFT_TIME_LIMIT: int = 3300  # 55分钟
    TASK_RESULT_EXPIRES: int = 86400  # 24小时
    MAX_RETRIES: int = 3
    
    # Whisper配置
    DEFAULT_MODEL_SIZE: Literal['tiny', 'base', 'small', 'medium', 'large'] = 'small'
    WHISPER_DEVICE: str = "cpu"  # cpu 或 cuda
    WHISPER_MODEL_CACHE_DIR: str = "/root/.cache/whisper"
    
    # 文件限制
    MAX_FILE_SIZE: str = "500M"
    MAX_VIDEO_DURATION: int = 7200  # 2小时
    TEMP_DIR: str = "/tmp/video_to_text"
    AUTO_CLEANUP: bool = True
    CLEANUP_INTERVAL: int = 3600  # 1小时
    
    # 下载配置
    DOWNLOAD_TIMEOUT: int = 600  # 10分钟
    YTDLP_OPTS: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }
    
    # FFmpeg配置
    FFMPEG_TIMEOUT: int = 300  # 5分钟
    AUDIO_SAMPLE_RATE: int = 16000
    AUDIO_CHANNELS: int = 1
    AUDIO_CODEC: str = "pcm_s16le"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 安全配置
    CORS_ORIGINS: list = ["*"]
    ALLOWED_VIDEO_DOMAINS: list = []  # 空列表表示允许所有域名
    RATE_LIMIT_PER_MINUTE: int = 10
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# 创建全局配置实例
settings = Settings()

# 构建 Redis URL
def get_redis_url() -> str:
    """获取Redis连接URL"""
    if settings.REDIS_PASSWORD:
        return f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"

# 日志配置
def setup_logging():
    """配置日志系统"""
    import logging
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT
    )
    
    # 设置第三方库日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("whisper").setLevel(logging.WARNING)

# 验证配置
def validate_settings():
    """验证配置的有效性"""
    errors = []
    
    # 检查端口范围
    if not 1 <= settings.API_PORT <= 65535:
        errors.append(f"无效的API端口: {settings.API_PORT}")
    
    # 检查Whisper设备
    if settings.WHISPER_DEVICE not in ['cpu', 'cuda']:
        errors.append(f"无效的Whisper设备: {settings.WHISPER_DEVICE}")
    
    # 检查时间限制
    if settings.TASK_SOFT_TIME_LIMIT >= settings.TASK_TIME_LIMIT:
        errors.append("软超时必须小于硬超时")
    
    if errors:
        raise ValueError(f"配置验证失败:\n" + "\n".join(errors))

# 打印配置信息（脱敏）
def print_settings():
    """打印当前配置（脱敏密码等敏感信息）"""
    print("\n=== 当前配置 ===")
    print(f"API地址: {settings.API_HOST}:{settings.API_PORT}")
    print(f"调试模式: {settings.DEBUG}")
    print(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    print(f"默认Whisper模型: {settings.DEFAULT_MODEL_SIZE}")
    print(f"Whisper设备: {settings.WHISPER_DEVICE}")
    print(f"最大文件大小: {settings.MAX_FILE_SIZE}")
    print(f"任务超时: {settings.TASK_TIME_LIMIT}秒")
    print(f"日志级别: {settings.LOG_LEVEL}")
    print("=" * 50 + "\n")