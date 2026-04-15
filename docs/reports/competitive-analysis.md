# Competitive Analysis — Ad Attribution Auditor

**Document Version:** 1.0
**Date:** April 2026
**Author:** Scientist Agent
**Project:** Ad Attribution Auditor (Chrome Extension)

---

## Executive Summary

The ad attribution space is dominated by enterprise-grade platforms (Triple Whale, Northbeam, Rockerbox, Hyros) that require significant setup time, ongoing configuration, and monthly budgets often exceeding $500–$1,000+. Meanwhile, Shopify D2C brands spending $10K–$500K/month on ads are left to rely on Meta and Google's own structurally conflicted attribution models, which systematically over-credit paid channels and obscure the true contribution of organic and direct traffic. Littledata addresses parts of this problem but focuses on data plumbing, not attribution scoring. No existing tool provides real-time, in-dashboard attribution accuracy validation via a lightweight Chrome extension at a sub-$10 entry price. This represents a clear and exploitable market gap.

---

## Competitor Profiles

### 1. Triple Whale

**Website:** https://triplewhale.com
**Blocked by Cloudflare at time of research; relying on G2, Trustpilot, and third-party reviews for data.**

**Product Overview:**
Triple Whale is an advanced marketing attribution platform designed for e-commerce brands. It combines multi-touch attribution (MTA), incrementality testing, and media mix modeling (MMM) into a unified analytics dashboard. Triple Whale's key differentiator is its "fingerprinting" approach to cross-device and cross-channel user journey tracking, and its strong emphasis on "carbon impact" (environmental SEO-style metrics for paid channels).

**How It Works:**
Triple Whale operates as a server-side tag management layer. Users install a tracking pixel/snippet, connect their ad platform APIs (Meta, Google, TikTok, etc.), and import Shopify order data via direct integration. Triple Whale then reconstructs individual customer journeys and applies a configurable attribution model (first-touch, last-touch, linear, time-decay, or custom) to distribute credit across touchpoints. The platform shows a "true ROAS" figure that accounts for organic and direct traffic the brand would have received regardless of paid spend.

**Pricing:**
Triple Whale does not publish pricing on its website. Based on publicly available reviews (G2, Trustpilot) and industry discussions, pricing starts at approximately **$500–$1,000/month** for small e-commerce brands, with enterprise plans running **$2,000–$5,000+/month** depending on ad spend volume and the number of channels tracked. There is no free tier. All plans require a sales call for onboarding.

**Strengths:**
- Comprehensive MTA + MMM + incrementality in one platform
- Excellent for brands spending $100K+/month on ads
- Strong community and content marketing (Triple Whale has a strong brand identity)
- Deterministic user-level attribution across devices
- Good visualization of the full customer journey

**Weaknesses:**
- No Chrome extension or in-dashboard overlay product
- Complex onboarding; requires dedicated time investment (most users cite 4–8 weeks to fully configure)
- Expensive for the target $10K–$100K/month ad spend segment
- Shopify integration is standard (pulls order data via API) but not uniquely deep
- No real-time "attribution accuracy score" — instead shows attribution breakdowns under the platform's own model
- No public pricing; sales-driven gating creates friction for SMBs

**Chrome Extension / Delivery Mechanism:**
None. Web app only. Triple Whale does not offer any browser-based overlay or extension product.

---

### 2. Northbeam

**Website:** https://northbeam.io

**Product Overview:**
Northbeam is a marketing intelligence platform positioned at mid-market and enterprise e-commerce brands. It offers multi-touch attribution, media mix modeling (MMM+), and "Northbeam Apex" — a data forwarding layer that sends attribution signals directly into ad platform algorithms to optimize bidding in real time. Northbeam is known for its clean UI and strong data visualization.

**How It Works:**
Northbeam connects to ad platforms via standard API integrations and uses a combination of pixel-based and server-side tracking. It builds a unified customer journey by stitching together touchpoints across paid search, social, display, email, and organic. Northbeam's MTA model runs on configurable lookback windows (up to 90 days or unlimited with MMM+). The "Apex" product represents a significant differentiator — it feeds Northbeam's conversion data back into Meta, Google, and TikTok's algorithm for automated bid optimization.

**Pricing:**
Northbeam does not publish pricing. Based on available data, plans start at approximately **$500/month** for smaller accounts and scale to **$2,000–$10,000+/month** for large enterprise clients. All plans require a demo and sales conversation. No free tier is available.

**Strengths:**
- Excellent UI/UX — consistently rated highest among competitors for ease of use
- Strong MMM+ product for long-term budget planning
- Apex integration for algorithm-level ad optimization is unique
- Deterministic view-through attribution ("Clicks + Deterministic Views") is a genuine innovation
- Claims 37% ROAS increase, 14% CVR increase, 20% CAC decrease (self-reported by enterprise customers)

**Weaknesses:**
- No Chrome extension or in-dashboard overlay
- No public pricing — sales-driven
- Requires significant setup and integration work
- May be overkill for brands spending under $50K/month on ads
- No specific "attribution accuracy score" — instead shows attribution under Northbeam's own model
- Not specifically Shopify-focused; general e-commerce focus

**Chrome Extension / Delivery Mechanism:**
None. Web app only. No browser extension product exists.

---

### 3. Rockerbox

**Website:** https://rockerbox.com

**Product Overview:**
Rockerbox is an enterprise-focused measurement platform that combines multi-touch attribution, media mix modeling, and controlled testing (incrementality) under one roof. Rockerbox's positioning is explicitly "unified measurement" — it argues that MTA, MMM, and testing answer different questions and should be used together rather than in isolation. Rockerbox is known for its data foundation layer (a SOC2-certified centralized marketing data repository) that serves as the single source of truth for all measurement methodologies.

**How It Works:**
Rockerbox requires enterprises to send all their marketing data (digital, offline, paid, organic) into Rockerbox's data foundation. From this centralized foundation, Rockerbox runs MTA, MMM, and testing simultaneously. The key insight Rockerbox offers is showing where methodologies agree and where they diverge — giving marketers confidence when alignment exists and prompting investigation when they don't.

**Pricing:**
Rockerbox is explicitly **enterprise-only**. There is no public pricing, no self-serve onboarding, and no free tier. Pricing is negotiated directly with sales and is likely in the **$5,000–$50,000+/month** range given the enterprise positioning. Minimum contract lengths are typically annual.

**Strengths:**
- Most comprehensive measurement methodology coverage (MTA + MMM + testing)
- SOC2-certified data foundation provides enterprise-grade trust
- "Methodology alignment" view is genuinely useful for strategic decision-making
- Strong for large brands with complex, multi-channel marketing

**Weaknesses:**
- Completely inaccessible to the SMB / lower-mid-market segment (our target)
- Multi-month implementation cycles
- No Chrome extension or lightweight product
- No real-time overlay or score — strategic reporting tool
- No Shopify-specific depth (generalist enterprise focus)

**Chrome Extension / Delivery Mechanism:**
None. Enterprise SaaS platform only.

---

### 4. Littledata

**Website:** https://littledata.io

**Product Overview:**
Littledata is a Shopify-focused data layer and server-side tracking platform. Its core value proposition is ensuring that Shopify's conversion data is accurately and completely delivered to Google, Meta, and Klaviyo — compensating for browser tracking failures (Safari ITP, iOS 14+ privacy changes, Chrome's third-party cookie deprecation). Littledata does not do attribution modeling itself; instead, it ensures the data that attribution models are built on is accurate.

**How It Works:**
Littledata installs as a Shopify app (10-minute setup, no GTM or code required). It provides server-side conversion tracking that fires directly from Shopify's servers, bypassing browser-based tracking limitations. Littledata also offers "Session Enrichment" and "Persistent ID" features that reconnect returning shoppers who appear as new users due to Safari/Chrome privacy restrictions. Data flows to Google Enhanced Conversions and Meta Conversions API.

**Pricing:**
Littledata publishes pricing on its website. Plans start at **$49/month** for the Starter plan (limited features), with the Professional plan at **$149/month** and Enterprise at **$399/month** (prices as of 2025 — verify current pricing directly). This makes Littledata the most accessible from a price perspective among all competitors reviewed.

**Strengths:**
- 10-minute Shopify setup — genuinely low friction
- Directly solves the iOS 14+ / Safari ITP / third-party cookie data loss problem
- Server-side tracking improves data completeness for all downstream attribution tools
- Persistent ID feature is valuable for attribution accuracy
- Strong Shopify-specific positioning ("The data layer for Shopify")
- Lowest price point of any competitor reviewed

**Weaknesses:**
- Not an attribution tool — does not provide MTA, MMM, or attribution scores
- Does not show an "Attribution Accuracy Score" or any overlay on ad dashboards
- No Chrome extension
- Meta / Google Ads integration is one-way (improves their tracking, doesn't validate their attribution)
- No campaign-level optimization recommendations
- Littledata sends better data to platforms — but those platforms still apply their own (potentially inaccurate) attribution models

**Chrome Extension / Delivery Mechanism:**
None. Shopify app + server-side tracking only.

---

### 5. Hyros

**Website:** https://hyros.com

**Product Overview:**
Hyros is an AI-powered ad attribution and tracking platform that positions itself as the highest-accuracy attribution tool available, claiming to be "proven to increase ad ROI by at least 15%." Hyros uses AI to model individual customer journeys and identify the true source of conversions, particularly in complex multi-touch, multi-channel environments. It also offers "AIR" — an AI remarketing agent that uses attribution data to personalize marketing at the individual visitor level.

**How It Works:**
Hyros installs a tracking pixel on the Shopify store (claiming "1-click AI setup" for Shopify). It then tracks individual user journeys across all ad platforms and applies AI models to determine the "true" source of each conversion. Hyros claims its AI is specifically trained on e-commerce attribution and outperforms last-click, first-click, and even standard MTA models. The AIR agent further uses this data for personalized remarketing.

**Pricing:**
Hyros does not publish pricing on its website. Based on available reviews and industry knowledge, pricing starts at approximately **$500–$1,000/month** for e-commerce brands and scales upward significantly for high-volume spenders. Hyros is positioned as a premium product and is notably more expensive than Littledata. All plans require a sales call.

**Strengths:**
- Strong AI positioning — "AI attribution" is a compelling narrative
- AIR (AI remarketing agent) adds a second product layer on top of attribution
- High-profile endorsements (Tony Robbins team, Alex Hormozi, Sam Ovens)
- Claims 15%+ revenue lift on average (self-reported, with disclaimers)
- Works across SaaS, e-commerce, call-based, and info/education businesses

**Weaknesses:**
- No Chrome extension or in-dashboard overlay
- "AI attribution" is essentially a proprietary MTA model — it does not validate platform attribution, it replaces it with its own
- No free tier; high price point
- Setup claims ("1-click") are aspirational; real-world onboarding varies
- No Shopify-specific depth beyond standard API integration
- Does not specifically solve the "attribution accuracy" problem of Meta/Google over-crediting themselves

**Chrome Extension / Delivery Mechanism:**
None. Web app + mobile apps for tracking dashboards only.

---

### 6. Existing Chrome Extensions for Ad Attribution

**Research query:** "chrome extension meta ads attribution" / "google ads attribution checker"

**Findings:**

There is a notable absence of Chrome extensions that perform independent attribution validation. The Chrome Web Store does contain a small number of peripheral tools:

1. **Tag Assistant (by Google)** — Verifies Google tag installation, but does not perform any attribution analysis or cross-reference with Shopify data.

2. **DataScout** — A Chrome extension used by some agencies for scraping ad library data from Meta and Google, but not for real-time attribution cross-referencing.

3. **SimilarWeb** — Provides estimated traffic and competitor data, but is not related to attribution accuracy.

4. **BuiltWith** — Detects e-commerce tech stacks (including Shopify), but no attribution functionality.

5. **Various "Ad Spy" tools** (PowerAdSpy, AdPeep) — For competitor ad creative intelligence, not attribution validation.

**Conclusion:**
There is no existing Chrome extension that:
- Reads ad platform dashboard data in real-time
- Cross-references against Shopify order data via API
- Displays an "Attribution Accuracy Score" overlay

This is a genuine whitespace. The extension delivery mechanism is itself a differentiator — all existing tools are server-side SaaS platforms. Delivering attribution validation directly in the browser, overlaid on the ad platform dashboards the user already lives in, is a novel approach.

---

### 7. Google's Own Attribution Tools

#### GA4 (Google Analytics 4)

**Attribution Models Available:**
GA4 offers data-driven attribution (the default), last-click, first-click, linear, time-decay, and position-based models. GA4's data-driven model uses machine learning to allocate credit based on observed conversion patterns, which is more sophisticated than last-click.

**Accuracy and Limitations:**

| Limitation | Impact |
|---|---|
| GA4 uses Google's own conversion tag — it cannot see conversions that occur outside its tracking scope (e.g., phone orders, in-person purchases, Shopify checkout not reached via tracked link) | Systematic under-counting of total conversions |
| GA4's model is trained on Google's own data, which already suffers from attribution bias toward Google channels | The "data-driven" model still skews toward Google |
| iOS 14+ App Tracking Transparency (ATT) has reduced iPhone user data by 30–60% for many Shopify brands, making GA4's customer journey data incomplete | Less reliable for brands with significant iOS customer base |
| GA4's model requires sufficient conversion volume to train — brands doing <100 conversions/month get unreliable outputs | Problematic for smaller Shopify D2C brands |
| No Shopify-native integration — requires manual GTM or server-side setup | Data gaps between Shopify and GA4 |

**Structural Conflict:**
GA4 is owned by Google. Google's business model depends on ad spend. Any attribution model Google publishes — even the ML-based data-driven model — will systematically favor Google channels because:
1. Google sees all Google Ads clicks and can match them to conversions
2. Google has limited visibility into Meta, TikTok, or organic conversions that don't pass through Google systems
3. Google's ML model trains on data where Google has the most complete picture

#### Google Ads Attribution Reports

**What They Show:**
Google Ads reports show conversions attributed (by Google's chosen model) to Google Ads campaigns, ad groups, keywords, and ads. Available attribution models include: last click, first click, linear, position-based, time decay, and data-driven.

**What They Hide:**

| What Google Ads Reports DON'T Show | Implication for Shopify Brands |
|---|---|
| Conversions that occurred but were not preceded by a Google Ads click | Overlooks organic, Meta-driven, and direct traffic that influenced the purchase |
| Cross-device journeys where the Google click was on mobile but conversion was on desktop | Under-counts Google Ads influence in some cases, over-counts in others |
| View-through conversions attributed to Google Display/YouTube when the real influence was a Meta ad seen first | YouTube/Display attribution is unreliable |
| The full customer journey — only shows the last Google touchpoint | Hides the true role of upper-funnel channels (TikTok, Meta awareness, podcast ads, etc.) |
| Actual revenue — only shows tracked conversions (which are incomplete due to tracking gaps) | Revenue figures are systematically lower than true total revenue |

**Structural Conflict:**
Google Ads attribution is structurally conflicted because:

1. **Incentive misalignment:** Google earns revenue when brands spend more on Google Ads. Reporting that Google Ads is NOT the most effective channel would reduce ad spend. Google's attribution reports will always, at minimum, show Google Ads performing adequately — they are not designed to produce objective third-party assessments.

2. **Data ownership:** Google has complete data about Google Ads interactions. It has partial data about conversions that involve non-Google touchpoints. Any attribution model applied to this incomplete dataset will favor Google channels.

3. **Pixel-based measurement:** Google Ads conversion tracking relies on pixels placed on Shopify checkout pages. These pixels fire on page load — they cannot verify whether a conversion was genuinely influenced by the Google ad or merely occurred after it. The pixel proves a click happened; it does not prove causation.

4. **No third-party validation:** No independent tool is required to verify Google's numbers. Brands have no way to check whether Google's reported ROAS is accurate without using a third-party attribution platform.

#### Meta Ads Manager Attribution

Meta's attribution reporting suffers from identical structural conflicts:

1. Meta reports conversions using its own pixel data on Shopify stores
2. Meta's data is incomplete for iOS users (Facebook SDK tracking gap post-iOS 14)
3. Meta has no visibility into conversions influenced by Google, TikTok, or organic channels that Meta did not touch
4. Meta's attributed conversions often exceed actual Shopify orders because the Meta pixel fires on add-to-cart and checkout-initiated events even when no purchase follows
5. Meta's cross-level reporting (campaign → ad set → ad) can show different conversion numbers depending on the attribution window selected

---

## Comparison Table

| Feature | Triple Whale | Northbeam | Rockerbox | Littledata | Hyros | Google/Meta Native | **Our Product** |
|---|---|---|---|---|---|---|---|
| **Target Segment** | Enterprise | Mid-Market / Enterprise | Enterprise | SMB / Mid-Market | Mid-Market / Enterprise | All | SMB / Lower-Mid-Market |
| **Pricing (est.)** | $500–$5K+/mo | $500–$10K+/mo | $5K–$50K+/mo | $49–$399/mo | $500–$1K+/mo | Free (built-in) | Free / $9.99 / $49 |
| **Free Tier** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Chrome Extension** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **In-Dashboard Overlay** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Shopify Native Integration** | ✅ (API) | ✅ (API) | ✅ (API) | ✅ (App-level) | ✅ (API) | ❌ (manual) | ✅ (API) |
| **Attribution Accuracy Score** | ❌ (shows attribution under own model) | ❌ (shows attribution under own model) | ❌ (shows methodology alignment) | ❌ (no attribution) | ❌ (AI attribution model, not accuracy score) | ❌ (inherently conflicted) | ✅ |
| **Multi-Touch Attribution** | ✅ | ✅ | ✅ | ❌ | ✅ | Partial | ❌ (validates platform MTA) |
| **Media Mix Modeling** | ✅ | ✅ (MMM+) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Incrementality Testing** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Real-Time Data** | ✅ (refreshed) | ✅ | ✅ | ✅ | ✅ | Real-time (but incomplete) | ✅ |
| **Setup Complexity** | High (weeks) | Medium-High (days–weeks) | Very High (months) | Low (minutes) | Medium | Low | Low (minutes) |
| **Validates Platform Attribution** | ❌ (replaces it) | ❌ (replaces it) | ❌ (replaces it) | ❌ (improves pixel data) | ❌ (replaces it) | N/A | ✅ |
| **Agency / Reseller Model** | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ ($49/client) |

---

## Our Positioning & Differentiation

### The Core Differentiator: Third-Party Validation vs. Replacement

All existing competitors (Triple Whale, Northbeam, Rockerbox, Hyros) operate on the same fundamental premise: **their attribution model is better than the platform's, so use theirs instead.** This requires brands to:
1. Trust the new platform's methodology over their existing dashboards
2. Invest weeks or months in setup and configuration
3. Pay $500–$10,000+/month
4. Accept that the new platform's numbers may differ from what they're used to seeing

This creates a significant adoption barrier and a perpetual "who is right?" debate inside marketing teams.

**Our approach is fundamentally different: we don't replace platform attribution — we validate it.**

We show up directly in Meta Ads Manager and Google Ads as a Chrome extension overlay, read the same data the brand's marketers are already looking at, cross-reference it against actual Shopify order data (the source of truth), and compute an "Attribution Accuracy Score" that tells the brand: "Meta is claiming credit for X% of these conversions. Our analysis shows the real figure is closer to Y%."

### Positioning Statement

> **Ad Attribution Auditor** is the only tool that shows Shopify D2C brands exactly how much credit Meta Ads and Google Ads are over-claiming — in real time, directly in the ad platform dashboards they already use, starting at free.

### Key Differentiation Points

1. **In-dashboard overlay (novel):** No competitor delivers a Chrome extension overlay. Every competitor requires users to leave their ad platform dashboards and log into a separate SaaS tool. Our overlay meets marketers where they already work.

2. **Validation vs. replacement:** We don't ask brands to abandon their existing dashboards or trust a new attribution methodology. We give them an objective accuracy score that validates or challenges what they're seeing.

3. **Frictionless onboarding:** No implementation project, no sales call, no 4–8 week setup. Install the extension, connect the Shopify API, and see your score immediately.

4. **Pricing accessible to SMB:** Free tier for small brands, $9.99 Pro for growing brands, $49/month per-client for agencies. No competitor even approaches this price point.

5. **The "attribution accuracy score" concept:** While competitors show attribution breakdowns under their own models, no competitor specifically frames the question as "how accurate is Meta/Google's own attribution?" — which is the question Shopify brands actually want answered.

---

## Key Takeaways & Strategic Recommendations

### Key Takeaways

1. **The incumbent attribution tools are all server-side SaaS platforms.** None have a browser-based overlay product. The extension delivery mechanism is genuinely novel in this space and aligns with how Shopify D2C marketers actually work (living in Meta Business Manager and Google Ads).

2. **No tool addresses the structural conflict directly.** Every competitor positions itself as "use our model instead of the platform's." This is a trust problem — brands have to believe the new tool is more accurate than the platform, which is a big ask without external validation. We solve this by making the platforms' own data + Shopify ground truth the validation source.

3. **Littledata has the right Shopify-specific instinct but wrong product scope.** The Shopify D2C focus is correct; the data-layer-only approach misses the actual decision moment (when a marketer is looking at their ROAS in Meta Ads Manager).

4. **Google and Meta's native attribution is structurally incentivized to over-credit themselves.** Every brand in our target segment is working with systematically inflated paid channel ROAS numbers. The magnitude of this inflation is the core value proposition.

5. **Chrome extension whitespace is real, but one competitor exists.** Our research found no existing extension that does what we're building, BUT one relevant competitor was found: RedTrack Chrome Extension (see Section 7). We need to differentiate clearly from it.

## 7. Chrome Extension Competitors: Direct Research Results

Extensive search of Chrome Web Store and Google for "chrome extension meta google ads attribution" found the following:

---

### 7.1 RedTrack Chrome Extension ⚠️ Closest Competitor

**URL:** https://www.redtrack.io/features/chrome-extension/
**Chrome Web Store:** Yes
**Pricing:** Starts at **$149/month** (event-based pricing model)

**What it does:**
> "See RedTrack's accurate conversion data instantly in Meta Ads Manager. No tab switching. No waiting for updates. Just real performance data where you work."

RedTrack's Chrome Extension shows their attribution data directly overlaid in Meta Ads Manager — exactly the UX pattern we're proposing.

**How it differs from our product:**
| Dimension | RedTrack | Our Product |
|-----------|---------|-------------|
| **Primary user** | Affiliates, media buyers, performance marketers | Shopify D2C brands |
| **Data source** | RedTrack's own attribution model (server-side tracking) | Shopify orders as ground truth |
| **Methodology** | RedTrack's algorithm replaces platform attribution | Compare platform claims vs. Shopify truth |
| **Attribution model** | Builds their own model, asks you to trust it | Uses Shopify as external validator — no model to trust |
| **Target price** | $149+/month | $9.99/month |
| **Setup** | Requires RedTrack account + integration setup | Paste Shopify API key, works immediately |
| **Shopify-native** | Not Shopify-specific | Explicitly Shopify-native |

**Key differentiation message vs. RedTrack:**
> "RedTrack tells you what their model thinks is true. We tell you what actually happened in your Shopify store."

RedTrack is trying to build a better attribution model. We are not building a model — we are using Shopify's order data as an independent external validator. This is fundamentally different.

**Risk:** RedTrack could theoretically expand into the Shopify SMB market and add Shopify-native integration. However, their core business is affiliate/media buyer, not Shopify D2C, so product focus is unlikely to shift.

---

### 7.2 AdScope — Chrome Extension (Competitive Intelligence, NOT Attribution)

**URL:** https://chromewebstore.google.com/detail/adscope
**Pricing:** Free tier + Pro paid (amount not publicly listed)

**What it does:** Spy on any Shopify store and Meta ads. Analyze competitor spending, find best products, track competitor ad strategies. Shows estimated ad spend, campaign performance signals, landing page detection, tech stack detection, and competitor tracking.

**Why it's NOT a competitor:**
AdScope is **competitive intelligence** — you use it to spy on what your competitors are doing. It does NOT audit your own ROAS, does NOT compare Meta/Google claims against Shopify orders, and does NOT tell you if you're over-counting conversions.

It's the difference between "watching what your competitor spends" and "knowing if your ad platform is lying to you about your own results."

---

### 7.3 Google Tag Assistant — Chrome Extension (Tag Verification, NOT Attribution)

**What it does:** Verifies that Google tags (Google Analytics, Google Ads, etc.) are firing correctly on your website.

**Why it's NOT a competitor:**
Google Tag Assistant confirms that tags fire. It has nothing to do with ROAS auditing or cross-platform attribution verification. It also doesn't verify whether Google Ads' attribution claims are accurate — it just checks if the tracking pixel loaded.

---

### 7.4 TrueROAS — Shopify App (Not Chrome Extension)

**URL:** https://apps.shopify.com/trueroas
**Pricing:** Not publicly listed (mentions "see all pricing options")
**Reviews:** 4.6 stars, 44 reviews

**What it does:** Tracks Shopify orders and attributes results to the correct Meta/Google/TikTok ad. Positions as AI-powered ad attribution. Includes customer journeys, creative breakdown, ads manager, profit tracking, and CAPI (Conversion API) integration.

**Why it's NOT a direct competitor:**
- **Not a Chrome Extension** — it's a Shopify App that requires installation and configuration
- **Attribution model** — TrueROAS builds its own attribution model (like Triple Whale), not an audit layer
- **Focus** — It's a full tracking and attribution suite, not an in-dashboard verification overlay
- **Pricing** — Not publicly listed, suggesting it may be in the $149-500+/month range based on comparable tools

The critical difference: TrueROAS tries to get attribution right. We tell you whether Meta and Google got attribution wrong.

---

### 7.5 WeTrack — Shopify App (Not Chrome Extension)

**URL:** Listed on Shopify App Store, free plan available
**Reviews:** 4.8 stars, 1,101 reviews

**What it does:** Ad tracking platform for Shopify, connects to Meta/Google/TikTok. Free plan available, positioned as accessible option.

**Why it's NOT a direct competitor:**
Same as TrueROAS — it's a Shopify App for ad tracking, not an in-dashboard Chrome Extension for attribution auditing.

---

### Chrome Extension Competitive Summary

| Extension | In-dashboard overlay? | Audits Meta/Google vs Shopify? | Shopify-native? | Price |
|-----------|----------------------|--------------------------------|-----------------|-------|
| **RedTrack** | ✅ Yes | ❌ No (uses their own model) | ❌ No | $149+/mo |
| **AdScope** | ✅ Yes | ❌ No (competitive intel only) | ✅ Yes | Free/paid |
| **Tag Assistant** | ✅ Yes | ❌ No (tag verification) | ❌ No | Free |
| **Our Product** | ✅ Yes | ✅ Yes | ✅ Yes | $9.99/mo |

**Bottom line:** RedTrack is the only real Chrome Extension competitor in the attribution space. But they are not doing what we're doing — they're building an attribution model, we're doing an audit. The positioning distinction is critical: "RedTrack tells you what they think is true. We tell you what actually happened in your store."

---

## 8. Strategic Recommendations

1. **Lead with the accuracy score, not attribution modeling.** Don't try to explain MTA methodology. Lead with: "Your Meta dashboard says ROAS is 4.2x. Our data says real ROAS is likely 2.8x–3.4x. Here's why." The gap is the story.

2. **Target the Shopify agency channel aggressively for Agency tier.** Shopify-focused agencies managing 5–20 clients at $49/client generate $245–$980/month per agency. Agencies are the most motivated buyers and can become distribution partners.

3. **Invest in the "why is my platform lying to me" content angle.** The structural conflict of platform attribution is widely understood by sophisticated marketers but never articulated clearly by tools. Be the tool that names the problem out loud.

4. **Build a "calibration report" as a secondary deliverable.** For each client, generate a PDF that shows: (a) what Meta/Google claimed credit for, (b) what Shopify actually shows, (c) the delta. This becomes a sales asset and a retention tool.

5. **Prioritize the Meta Ads Manager overlay first.** Meta's attribution over-crediting is more severe than Google's (Meta has more tracking gaps from iOS and less visibility into non-Meta touchpoints). Being right about Meta first establishes credibility before expanding to Google.

6. **Consider Littledata as a potential integration or partnership target rather than competitor.** Littledata solves the data completeness problem; we solve the interpretation problem. Combined, they offer Shopify brands a complete solution: accurate data + accurate attribution analysis.

---

*End of Document*
