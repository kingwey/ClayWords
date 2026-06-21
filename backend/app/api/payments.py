"""Payment API - Alipay integration and callbacks"""

from typing import Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.api.auth import get_current_user, UserInfo
from app.db.session import get_session
from app.models.entities import Order, IdempotencyKey
from app.services.payment.payment_service import get_payment_service, PaymentService
from app.services.order import update_order_status, OrderStatus


router = APIRouter(prefix="/payments", tags=["payments"])


class CreatePaymentRequest(BaseModel):
    """创建支付请求"""
    order_id: str
    payment_method: str = "alipay"  # alipay / wechat


class CreatePaymentResponse(BaseModel):
    """创建支付响应"""
    order_id: str
    pay_url: str
    trade_no: str
    qr_code: Optional[str] = None
    expires_in: int = 1800  # 30 分钟


class RefundRequest(BaseModel):
    """退款请求"""
    order_id: str
    refund_amount: Optional[float] = None  # None = 全额退款
    refund_reason: str


@router.post("/create", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """
    创建支付

    Phase Q6.1.1: 集成支付宝沙箱

    流程:
    1. 验证订单属于当前用户
    2. 验证订单状态（pending/confirmed）
    3. 调用支付宝 API 生成支付链接
    4. 返回 pay_url 或二维码
    """
    # 查找订单
    stmt = select(Order).where(
        Order.order_id == request.order_id,
        Order.user_id == current_user.user_id
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # 验证订单状态
    if order.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态为「{order.status}」，无法支付"
        )

    # 检查是否已支付
    if order.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="订单已支付"
        )

    # 创建支付交易
    try:
        payment_result = payment_service.create_trade(
            order_id=order.order_id,
            total_amount=order.total_price,
            subject=f"陶语订单 - {order.order_id[:8]}",
            body=f"陶瓷定制服务"
        )

        return CreatePaymentResponse(
            order_id=order.order_id,
            pay_url=payment_result["pay_url"],
            trade_no=payment_result["trade_no"],
            qr_code=payment_result.get("qr_code"),
            expires_in=1800,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建支付失败: {str(e)}"
        )


@router.post("/callback")
async def payment_callback(
    request: Request,
    session: AsyncSession = Depends(get_session),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """
    支付回调处理

    Phase Q6.1.2: 验签 + 幂等 + 状态机迁移

    支付宝会发送 POST 表单数据，包含:
    - out_trade_no: 商户订单号
    - trade_no: 支付宝交易号
    - trade_status: 交易状态 (TRADE_SUCCESS / TRADE_FINISHED)
    - total_amount: 交易金额
    - buyer_pay_amount: 买家付款金额
    - sign: RSA2 签名
    """
    # 获取表单参数
    form_data = await request.form()
    params = dict(form_data)

    # 验证签名
    if not payment_service.verify_callback(params):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="签名验证失败"
        )

    out_trade_no = params.get("out_trade_no")
    trade_no = params.get("trade_no")
    trade_status = params.get("trade_status")
    total_amount = params.get("total_amount")

    if not out_trade_no:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少订单号"
        )

    # 幂等性检查
    idempotency_key = f"payment_callback_{trade_no}"
    stmt = select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # 已处理过，返回成功（支付宝要求返回 success）
        return "success"

    # 记录幂等性键
    idem_key = IdempotencyKey(
        key=idempotency_key,
        metadata={
            "out_trade_no": out_trade_no,
            "trade_no": trade_no,
            "trade_status": trade_status,
            "total_amount": total_amount,
        }
    )
    session.add(idem_key)

    # 查找订单
    stmt = select(Order).where(Order.order_id == out_trade_no)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        await session.commit()
        return "success"  # 订单不存在，但返回成功避免支付宝重试

    # 处理支付状态
    if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        # 支付成功
        if order.status in ["pending", "confirmed"]:
            # 状态迁移：pending/confirmed → paid (使用 dispatched 代替)
            order.status = "dispatched"  # 已支付，进入派单流程
            order.updated_at = datetime.utcnow()

            # 可选：记录支付信息到订单
            # order.payment_trade_no = trade_no
            # order.paid_amount = float(total_amount)
            # order.paid_at = datetime.utcnow()

    await session.commit()

    # 支付宝要求返回 "success" 字符串
    return "success"


@router.post("/refund")
async def refund_payment(
    request: RefundRequest,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """
    发起退款

    Phase Q6: 支付宝退款接口

    流程:
    1. 验证订单属于当前用户
    2. 验证订单状态（已支付）
    3. 调用支付宝退款 API
    4. 更新订单状态为 refunding
    """
    # 查找订单
    stmt = select(Order).where(
        Order.order_id == request.order_id,
        Order.user_id == current_user.user_id
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # 验证订单状态（必须已支付）
    if order.status not in ["dispatched", "producing", "completed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"订单状态为「{order.status}」，无法退款"
        )

    # 退款金额
    refund_amount = request.refund_amount or order.total_price

    if refund_amount > order.total_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="退款金额超过订单金额"
        )

    # 调用退款接口
    try:
        refund_result = payment_service.refund_trade(
            order_id=order.order_id,
            refund_amount=refund_amount,
            refund_reason=request.refund_reason
        )

        if refund_result.get("success"):
            # 更新订单状态
            order.status = "refunding"
            order.updated_at = datetime.utcnow()
            await session.commit()

            return {
                "status": "success",
                "order_id": order.order_id,
                "refund_no": refund_result["refund_no"],
                "refund_amount": refund_amount,
                "message": "退款申请已提交"
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="退款失败"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"退款失败: {str(e)}"
        )


@router.get("/{order_id}/status")
async def query_payment_status(
    order_id: str,
    current_user: UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    payment_service: PaymentService = Depends(get_payment_service),
):
    """
    查询支付状态

    Phase Q6: 主动查询交易状态（用于前端轮询）
    """
    # 验证订单属于当前用户
    stmt = select(Order).where(
        Order.order_id == order_id,
        Order.user_id == current_user.user_id
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="订单不存在"
        )

    # 查询支付状态
    trade_info = payment_service.query_trade(order_id)

    if trade_info:
        return {
            "order_id": order_id,
            "order_status": order.status,
            "trade_no": trade_info.get("trade_no"),
            "trade_status": trade_info.get("trade_status"),
            "total_amount": trade_info.get("total_amount"),
            "paid": order.status in ["dispatched", "producing", "completed", "shipped", "delivered"],
        }

    return {
        "order_id": order_id,
        "order_status": order.status,
        "paid": False,
    }
