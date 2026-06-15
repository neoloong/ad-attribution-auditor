export interface MetaAdsRow {
  date: string;
  campaign_name: string;
  spend: number;
  reported_conversions: number;
  reported_revenue: number;
  reported_roas: number;
}

export interface GoogleAdsRow {
  date: string;
  campaign_name: string;
  spend: number;
  reported_conversions: number;
  reported_revenue: number;
  cost_per_conversion: number;
}

export interface ShopifyOrderRow {
  date: string;
  order_id: string;
  email: string;
  created_at: string;
  revenue: number;
  referring_site: string;
  landing_site: string;
}

export interface GSCRow {
  date: string;
  query: string;
  clicks: number;
  impressions: number;
}

export interface SearchTermRow {
  search_term: string;
  campaign_name: string;
  spend: number;
  reported_conversions: number;
  impressions: number;
  clicks: number;
  reported_revenue: number;
  ad_group: string;
}

export interface AdDaily {
  date: string;
  spend: number;
  reportedConversions: number;
  reportedRevenue: number;
}

export interface ShopifyDaily {
  date: string;
  actualConversions: number;
  actualRevenue: number;
}

export interface GSCDaily {
  date: string;
  brandClicks: number;
  brandImpressions: number;
}
