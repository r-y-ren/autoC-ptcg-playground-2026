"""天梯回读三要素校验（μ/日期/官方 URL）→分片格式（R10）"""
from __future__ import annotations


def validate_ladder_readback(readback):
    """校验人工回读录入 {ladder_mu, ladder_mu_date, source_url}：
    μ 数值且 0≤μ≤3000 合理域；日期 ISO；URL http(s)。三要素缺一抛异常。
    通过→分片 dict（数字纪律：每个数字带 source）。
    """
    for key in ("ladder_mu", "ladder_mu_date", "source_url"):
        if key not in readback:
            raise ValueError(f"回读缺三要素之一: {key}")
    mu = readback["ladder_mu"]
    if not isinstance(mu, (int, float)) or not (0 <= mu <= 3000):
        raise ValueError(f"ladder_mu 超合理域 [0,3000]: {mu}")
    date = str(readback["ladder_mu_date"])
    if len(date) != 10 or date[4] != "-" or date[7] != "-":
        raise ValueError(f"ladder_mu_date 非 ISO 日期: {date}")
    url = str(readback["source_url"])
    if not url.startswith(("http://", "https://")):
        raise ValueError(f"source_url 非 http(s): {url}")
    return {
        "category": "ladder-readback",
        "metrics": {"ladder_mu": mu, "ladder_mu_date": date},
        "source": url,
    }
