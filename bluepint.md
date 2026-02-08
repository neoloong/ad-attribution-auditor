# 🚀 Project Blueprint: AI-Driven Marketing Auditor & Predictor

## 1. 项目愿景 (Vision)
构建一个**“第三方广告归因审计与预判引擎”**。旨在打破大厂（Google/Meta）的数据黑盒，帮助中小型电商（SMB/Mid-market）通过独立的算法视角，还原真实的广告增量价值（Incrementality），并利用 AI 在投放前预测素材 ROI。

* **Slogan:** "Don't let Big Tech grade their own homework." (别让大厂既当运动员又当裁判)
* **核心价值:** 透明度 (Transparency)、去水分 (De-duplication)、增量思维 (Incrementality)。

## 2. 开发者背景与约束 (Developer Context)
* **角色:** 单人开发者 (Solo Founder)，在职大厂 Applied Scientist (背景：Google PCM, Amazon MADS)。
* **核心能力:** pCVR 建模、归因算法、LLM 应用、隐私计算 (Privacy Sandbox)。
* **资源:** $100k 启动资金，2-3 年时间窗口（Side Hustle 模式）。
* **策略:** 避免在大厂重资源领域（如企业级定制）竞争，专注轻量级、算法驱动的 SaaS 工具。

## 3. 产品架构 (Product Architecture)
产品由两个核心引擎组成，形成闭环：

### Engine A: The Auditor (归因审计器 - 后验)
* **输入:**
    * 广告平台数据 (Meta/Google Ads CSV/API)。
    * 第一方交易数据 (Shopify Orders)。
    * 自然流量数据 (Google Search Console / Brand Search Reports)。
* **核心算法逻辑:**
    1.  **去重 (De-duplication):** 识别跨渠道的重复转化归因。
    2.  **防抢功 (Cannibalization Detection):** 重点识别“自然意向用户”被广告收割的现象。
        * *逻辑示例:* 如果用户在点击 Meta 广告前 24 小时内已搜索过“品牌词”，则判定该广告转化的增量价值 (Incremental Value) 为低。
    3.  **真实 ROI 计算:** 输出 `Reported ROAS` vs `True Incremental ROAS`。

### Engine B: The Predictor (ROI 预判器 - 先验)
* **输入:** 广告素材 (图片/文案) + 目标受众标签 + 行业基准数据。
* **核心算法逻辑:**
    1.  **LLM 特征提取:** 使用多模态模型分析素材的“痛点”、“利益点”、“语气”等特征向量。
    2.  **pCVR 模拟:** 结合行业 Prior 和历史数据，预测该素材的点击率 (CTR) 和转化率 (CVR)。
    3.  **Pre-flight 建议:** 在投放前给出 ROI 预测范围和优化建议。

## 4. 目标客户 (Target Audience)
* **核心画像:** 年营收 $1M - $10M 的 Shopify 独立站卖家、D2C 品牌。
* **痛点:**
    * 不信任 Meta/Google 后台夸张的 ROAS 数据。
    * Shopify 自带归因过于简单 (Last-click)，漏掉助攻。
    * 没有预算雇佣 Data Scientist 做增量实验。

## 5. 开发路线图 (Roadmap)

### Phase 1: MVP 原型 (Month 1-6)
* **形式:** Python 脚本 / Jupyter Notebook / Streamlit Web App。
* **功能:**
    * 支持上传 CSV (Meta Ads Report, Google Search Report, Shopify Orders)。
    * 运行基础的“时间窗口重合分析” (Time-window Overlap Analysis)。
    * 输出简单的文本报告：“Meta 夸大了 30% 的效果”。
* **技术栈:** Python, Pandas, OpenAI API (用于生成自然语言建议)。

### Phase 2: 自动化与 SaaS 化 (Month 7-12)
* **形式:** Shopify App 插件。
* **功能:**
    * 对接 Marketing API 自动拉取数据。
    * 增加 Dashboard 可视化。
    * 引入 LLM 进行素材分析与 ROI 预测。

### Phase 3: 规模化与融资 (Month 13+)
* **目标:** 获取 20-50 个付费客户，验证模型准确性。
* **高级功能:** 引入 Data Clean Room 概念，支持更复杂的隐私计算；支持更多渠道 (TikTok, Email)。

## 6. MVP 核心代码逻辑 (用于 AI 开发参考)

```python
# Core Logic: Attribution Audit & Cannibalization Check
# 目标: 找出被 Meta 认领但实际上由 Brand Search 驱动的订单

def audit_attribution(orders_df, meta_clicks_df, brand_search_df):
    """
    params:
    - orders_df: 包含 order_id, user_id/email_hash, timestamp, revenue
    - meta_clicks_df: 包含 user_id/email_hash, timestamp, cost
    - brand_search_df: 包含 user_id/email_hash, timestamp (High Intent Signal)
    """
    
    # 1. Meta Self-Attribution (模拟大厂逻辑: 7-day click)
    meta_claimed = merge_and_filter(orders_df, meta_clicks_df, window_days=7)
    
    # 2. Cannibalization Check (审计逻辑)
    # 检查在 Meta 点击 *之前* 的短时间内 (如 24h) 是否有品牌词搜索
    audit_result = check_overlap(meta_claimed, brand_search_df, lookback_window_hours=24)
    
    # 3. Calculate Incremental Metrics
    total_revenue = meta_claimed['revenue'].sum()
    cannibalized_revenue = audit_result[audit_result['is_cannibalized']]['revenue'].sum()
    
    true_incremental_revenue = total_revenue - cannibalized_revenue
    
    return {
        "reported_revenue": total_revenue,
        "cannibalized_revenue": cannibalized_revenue,
        "true_revenue": true_incremental_revenue,
        "inflation_rate": cannibalized_revenue / total_revenue
    }
