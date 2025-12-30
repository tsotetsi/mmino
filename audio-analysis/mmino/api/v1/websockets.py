"""
WebSocket endpoints for real-time updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
import asyncio
from datetime import datetime
import logging

from mmino.db.session import get_db
from mmino.schemas import JobResponse
from mmino.db import crud

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected")
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
    
    async def broadcast(self, message: dict):
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to user {user_id}: {e}")

manager = ConnectionManager()

@router.websocket("/ws/jobs/{user_id}")
async def websocket_job_updates(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time job updates
    """
    await manager.connect(websocket, user_id)
    
    try:
        # Send initial list of active jobs
        db = next(get_db())
        active_jobs = crud.get_user_jobs(db, user_id, status="active", limit=10)
        
        for job in active_jobs:
            await websocket.send_json({
                "type": "job_update",
                "data": JobResponse.from_orm(job).dict(),
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Keep connection alive and listen for messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message.get("type") == "subscribe_job":
                    job_id = message.get("job_id")
                    # Start sending updates for specific job
                    await subscribe_to_job(websocket, user_id, job_id)
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        manager.disconnect(websocket, user_id)

async def subscribe_to_job(websocket: WebSocket, user_id: str, job_id: str):
    """
    Send periodic updates for a specific job
    """
    db = next(get_db())
    
    try:
        while True:
            job = crud.get_job_by_id(db, job_id)
            if not job or str(job.user_id) != user_id:
                await websocket.send_json({
                    "type": "error",
                    "message": "Job not found or access denied"
                })
                break
            
            await websocket.send_json({
                "type": "job_progress",
                "job_id": job_id,
                "progress": job.progress,
                "status": job.status.value,
                "estimated_time_remaining": None,  # Could calculate based on progress
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # If job is completed or failed, stop updates
            if job.status in ["completed", "failed", "cancelled"]:
                await websocket.send_json({
                    "type": "job_completed",
                    "job_id": job_id,
                    "status": job.status.value,
                    "download_url": f"/api/v1/download/{job_id}" if job.status == "completed" else None,
                    "timestamp": datetime.utcnow().isoformat()
                })
                break
            
            # Wait before next update
            await asyncio.sleep(5)  # Update every 5 seconds
    
    except Exception as e:
        logger.error(f"Error in job subscription for {job_id}: {e}")

@router.websocket("/ws/system")
async def websocket_system_updates(websocket: WebSocket):
    """
    WebSocket for system-wide updates (admin only)
    """
    await websocket.accept()
    
    try:
        # Send initial system stats
        db = next(get_db())
        stats = crud.get_system_stats(db)
        
        await websocket.send_json({
            "type": "system_stats",
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep connection alive
        while True:
            await asyncio.sleep(30)  # Send updates every 30 seconds
            
            # Get updated stats
            stats = crud.get_system_stats(db)
            await websocket.send_json({
                "type": "system_stats_update",
                "data": stats,
                "timestamp": datetime.utcnow().isoformat()
            })
    
    except WebSocketDisconnect:
        logger.info("Admin WebSocket disconnected")
    except Exception as e:
        logger.error(f"System WebSocket error: {e}")
    finally:
        db.close()

@router.get("/ws/test")
async def test_websocket():
    """
    Test endpoint to verify WebSocket setup
    """
    return {
        "message": "WebSocket endpoints are available",
        "endpoints": {
            "user_jobs": "/ws/jobs/{user_id}",
            "system": "/ws/system"
        }
    }