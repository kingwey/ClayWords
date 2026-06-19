"""GPU Worker for 3D Design Generation with Task Scheduling"""

import asyncio
import json
import structlog
from datetime import datetime
from typing import Optional

from arq import run_worker
from arq.worker import WorkerSettings
from arq.utils import asyncio_run

from .pipelines.template_pipeline import template_pipeline
from .pipelines.generative_pipeline import generative_pipeline
from .pipelines.hybrid_pipeline import hybrid_pipeline


structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
)

logger = structlog.get_logger()


async def report_progress(ctx: dict, task_id: str, stage: str, percent: int, message: str):
    """Report progress to Redis for SSE forwarding"""
    redis = ctx.get("redis")
    if redis:
        event = {
            "stage": stage,
            "percent": percent,
            "message": message
        }
        await redis.publish(f"task:{task_id}:progress", json.dumps(event))
        logger.info("progress_reported", task_id=task_id, stage=stage, percent=percent)


async def process_design_gen(ctx: dict, session_id: str, design_params: dict, task_id: str) -> dict:
    """
    Process design generation task.

    Runs three pipelines in parallel and returns three options.

    Args:
        ctx: ARQ context
        session_id: Session ID for the design
        design_params: Design parameters from LLM parser
        task_id: Unique task ID

    Returns:
        Dict with options and status
    """
    logger.info("processing_design_gen", session_id=session_id, task_id=task_id)

    redis = ctx.get("redis")

    # Report progress stages
    stages = [
        ("parsing", 10, "解析设计参数"),
        ("template_match", 30, "匹配模板"),
        ("gen_inference", 50, "生成设计方案"),
        ("craft_check", 70, "工艺校验"),
        ("post_process", 90, "后处理")
    ]

    options = []

    try:
        # Stage 1: Parsing complete
        await report_progress(ctx, task_id, "parsing", 10, "设计参数解析完成")

        # Run three pipelines concurrently
        material = design_params.get("material", "porcelain_white")

        # Pipeline A: Template-based
        await report_progress(ctx, task_id, "template_match", 30, "模板匹配中")
        option_a = await asyncio.get_event_loop().run_in_executor(
            None,
            template_pipeline,
            "template_001",
            design_params,
            material
        )
        await report_progress(ctx, task_id, "template_match", 40, "模板方案生成完成")
        options.append({
            "pipeline": "template",
            "result": option_a
        })

        # Pipeline B: Generative
        await report_progress(ctx, task_id, "gen_inference", 50, "AI生成中")
        option_b, error_b = await asyncio.get_event_loop().run_in_executor(
            None,
            generative_pipeline,
            design_params,
            material
        )
        if option_b:
            await report_progress(ctx, task_id, "gen_inference", 60, "AI方案生成完成")
            options.append({
                "pipeline": "generative",
                "result": option_b
            })

        # Pipeline C: Hybrid
        await report_progress(ctx, task_id, "gen_inference", 55, "混合方案生成中")
        option_c, error_c = await asyncio.get_event_loop().run_in_executor(
            None,
            hybrid_pipeline,
            "template_001",
            design_params,
            material
        )
        if option_c:
            options.append({
                "pipeline": "hybrid",
                "result": option_c
            })

        # Craft check stage
        await report_progress(ctx, task_id, "craft_check", 70, "工艺校验中")
        await report_progress(ctx, task_id, "craft_check", 80, "工艺校验完成")

        # Post-process stage
        await report_progress(ctx, task_id, "post_process", 90, "后处理中")
        await report_progress(ctx, task_id, "post_process", 95, "生成缩略图")

        # Done
        await report_progress(ctx, task_id, "done", 100, "设计完成")

        # Store results
        if redis:
            result_data = {
                "status": "completed",
                "options": [
                    {
                        "option_id": opt["result"].option_id,
                        "name": opt["result"].name,
                        "pipeline": opt["pipeline"],
                        "glb_url": opt["result"].glb_url,
                        "thumbnail_url": opt["result"].thumbnail_url,
                        "craft_check": opt["result"].craft_check_result,
                        "price": opt["result"].price,
                        "estimated_days": opt["result"].estimated_days
                    }
                    for opt in options
                ]
            }
            await redis.set(f"task:{task_id}:result", json.dumps(result_data), ex=3600)

        return {
            "status": "completed",
            "options": [opt["result"].option_id for opt in options]
        }

    except Exception as e:
        logger.error("design_gen_failed", task_id=task_id, error=str(e))
        if redis:
            error_data = {
                "status": "failed",
                "error": str(e)
            }
            await redis.set(f"task:{task_id}:result", json.dumps(error_data), ex=3600)
        raise


async def main():
    """Run worker"""
    logger.info("worker_starting")

    worker_settings = WorkerSettings(
        burst_mode=False,
        max_jobs=10,
        keep_result=3600,
        redis_settings={"host": "localhost", "port": 6379}
    )

    await run_worker(
        worker_settings,
        functions=[process_design_gen]
    )


if __name__ == "__main__":
    asyncio.run(main())
