"""测试 Hunyuan3D API 接口

验证 API Key 配置和接口连通性
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.hunyuan3d.client import hunyuan3d_client
from app.services.hunyuan3d.schemas import SubmitRequest
from app.core.config import settings


async def test_text_to_3d():
    """测试文本生成 3D"""
    print("=" * 60)
    print("测试 Hunyuan3D API - 文本生成 3D")
    print("=" * 60)

    # 检查配置
    if not settings.HUNYUAN3D_API_KEY:
        print("错误: 未配置 HUNYUAN3D_API_KEY")
        print("   请在 .env 文件中添加: HUNYUAN3D_API_KEY=sk-xxx")
        return

    print(f"API Key 已配置: {settings.HUNYUAN3D_API_KEY[:10]}...")
    print(f"Base URL: {settings.HUNYUAN3D_BASE_URL}")
    print()

    # 提交任务
    request = SubmitRequest(Prompt="一只可爱的小狗", Model="3.0")
    print(f"提交任务: {request.model_dump()}")

    try:
        submit_response = await hunyuan3d_client.submit(request)
        print(f"任务已提交，JobId: {submit_response.JobId}")
    except Exception as e:
        print(f"提交任务失败: {e}")
        return

    # 轮询结果
    job_id = submit_response.JobId
    max_attempts = 120  # 10 分钟
    print(f"\n开始轮询任务状态（最多 {max_attempts * 5 / 60:.0f} 分钟）...")
    print()

    for i in range(max_attempts):
        await asyncio.sleep(5)

        try:
            query_response = await hunyuan3d_client.query(job_id)
            status = query_response.Status

            print(f"[{i+1}/{max_attempts}] 状态: {status:12}")

            if query_response.is_completed:
                print()
                print("=" * 60)
                print("生成完成！")

                glb_url = query_response.get_glb_url()
                obj_url = query_response.get_obj_url()

                if glb_url:
                    print(f"GLB 文件: {glb_url}")
                if obj_url:
                    print(f"OBJ 文件: {obj_url}")

                if query_response.ResultFile3Ds:
                    for file in query_response.ResultFile3Ds:
                        if file.PreviewImageUrl:
                            print(f"预览图 ({file.Type}): {file.PreviewImageUrl}")

                print(f"消耗积分: {query_response.ResultCreditConsumed}")
                print("=" * 60)
                return glb_url or obj_url

            elif query_response.is_failed:
                print()
                print("=" * 60)
                print(f"任务失败: {query_response.ErrorMessage}")
                print(f"错误代码: {query_response.ErrorCode}")
                print("=" * 60)
                return None

        except Exception as e:
            print(f"[{i+1}/{max_attempts}] 查询失败: {e}")
            continue

    print()
    print("=" * 60)
    print("超时：10 分钟后任务仍未完成")
    print("=" * 60)
    return None


async def test_image_to_3d():
    """测试图片生成 3D"""
    print("=" * 60)
    print("测试 Hunyuan3D API - 图片生成 3D")
    print("=" * 60)

    # 示例图片 URL（需替换为真实图片）
    test_image_url = "https://example.com/dog.jpg"
    print(f"⚠️  需要真实图片 URL，当前示例: {test_image_url}")
    print("   跳过图片测试")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Hunyuan3D API 测试脚本")
    print("=" * 60 + "\n")

    # 测试文本生成
    asyncio.run(test_text_to_3d())

    print("\n")

    # 测试图片生成（可选）
    # asyncio.run(test_image_to_3d())

    print("\n测试完成\n")
