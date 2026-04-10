"""认证服务模块"""

import os
from fastapi import HTTPException, Header

# API Key 配置
API_KEY = os.environ.get("API_KEY", "").strip()


def verify_api_key(x_api_key: str = Header(None)):
    """验证API Key"""
    if not API_KEY:
        return  # 未配置API Key时跳过验证
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="无效的API Key")
