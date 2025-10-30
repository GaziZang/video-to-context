from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, Literal
import redis
import json
import uuid
from datetime import datetime
from celery_tasks import process_video_task
import os

app = FastAPI(
    title="视频转文字API",
    description="基于 yt-dlp + FFmpeg + Whisper 的视频转文字服务",
    version="1.0.0"
)

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis连接
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)

class TaskRequest(BaseModel):
    video_url: HttpUrl
    output_format: Literal['txt', 'srt'] = 'txt'
    language: Optional[str] = None  # 可选：指定语言代码如 'zh', 'en'
    model_size: Literal['tiny', 'base', 'small', 'medium', 'large'] = 'small'
    
    @validator('video_url')
    def validate_url(cls, v):
        url_str = str(v)
        # 基本安全检查
        if any(char in url_str for char in ['&', '|', ';', '`', '$', '(', ')']):
            raise ValueError('URL包含非法字符')
        return v

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # processing, completed, failed
    progress: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str

@app.get("/")
async def root():
    """返回Web前端页面"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {
        "service": "视频转文字API",
        "version": "1.0.0",
        "status": "running",
        "message": "Web界面文件未找到，请访问 /docs 查看API文档",
        "endpoints": {
            "api_docs": "/docs",
            "submit_task": "POST /api/tasks",
            "get_task": "GET /api/tasks/{task_id}",
            "health": "GET /health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "redis": "disconnected", "error": str(e)}
        )

@app.post("/api/tasks", response_model=TaskResponse, status_code=202)
async def create_task(request: TaskRequest):
    """
    提交视频转文字任务
    
    - **video_url**: 视频链接（支持YouTube、B站等平台）
    - **output_format**: 输出格式（txt或srt）
    - **language**: 可选，指定语言代码提高准确率
    - **model_size**: Whisper模型大小（tiny/base/small/medium/large）
    """
    try:
        # 生成唯一任务ID
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # 初始化任务状态
        task_data = {
            'task_id': task_id,
            'video_url': str(request.video_url),
            'output_format': request.output_format,
            'language': request.language,
            'model_size': request.model_size,
            'status': 'processing',
            'progress': '任务已提交，等待处理',
            'created_at': created_at,
            'updated_at': created_at
        }
        
        # 保存到Redis
        redis_client.setex(
            f'task:{task_id}',
            3600 * 24,  # 24小时过期
            json.dumps(task_data)
        )
        
        # 提交到Celery异步任务队列
        process_video_task.apply_async(
            args=[task_id, str(request.video_url), request.output_format, 
                  request.language, request.model_size],
            task_id=task_id
        )
        
        return TaskResponse(
            task_id=task_id,
            status='processing',
            created_at=created_at,
            message='任务已提交，正在处理中'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'任务创建失败: {str(e)}')

@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    查询任务状态和结果
    
    - **task_id**: 任务ID
    """
    try:
        # 从Redis获取任务信息
        task_data_str = redis_client.get(f'task:{task_id}')
        
        if not task_data_str:
            raise HTTPException(status_code=404, detail='任务不存在或已过期')
        
        task_data = json.loads(task_data_str)
        
        return TaskStatusResponse(
            task_id=task_data['task_id'],
            status=task_data['status'],
            progress=task_data.get('progress'),
            result=task_data.get('result'),
            error=task_data.get('error'),
            created_at=task_data['created_at'],
            updated_at=task_data['updated_at']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'查询失败: {str(e)}')

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """删除任务记录"""
    try:
        deleted = redis_client.delete(f'task:{task_id}')
        if deleted:
            return {"message": "任务已删除", "task_id": task_id}
        else:
            raise HTTPException(status_code=404, detail='任务不存在')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'删除失败: {str(e)}')

if __name__ == "__main__":
    import uvicorn
    # 确保static目录存在
    os.makedirs("static", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)