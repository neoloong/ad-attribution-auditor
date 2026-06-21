import { describe, it, expect } from "vitest";
import {
  normalizeMetaAds,
  normalizeGoogleAds,
  normalizeShopifyOrders,
  normalizeGSC,
  mergeAdDaily,
} from "../normalizer";

describe("normalizeMetaAds", () => {
  it("parses valid Meta Ads CSV", () => {
    const csv = `Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value
2024-01-01,Campaign A,100.50,5,500
2024-01-02,Campaign B,0,0,0`;

    const result = normalizeMetaAds(csv);
    expect(result).toHaveLength(2);
    expect(result[0].date).toBe("2024-01-01");
    expect(result[0].spend).toBe(100.5);
    expect(result[0].reportedConversions).toBe(5);
    expect(result[0].reportedRevenue).toBe(500);
  });

  it("aggregates multiple rows for the same date", () => {
    const csv = `Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value
2024-01-01,Campaign A,100,3,300
2024-01-01,Campaign B,50,2,200`;

    const result = normalizeMetaAds(csv);
    expect(result).toHaveLength(1);
    expect(result[0].spend).toBe(150);
    expect(result[0].reportedConversions).toBe(5);
    expect(result[0].reportedRevenue).toBe(500);
  });

  it("handles dollar signs in amounts", () => {
    const csv = `Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value
2024-01-01,Campaign A,"$1,234.56",10,"$5,000"`;

    const result = normalizeMetaAds(csv);
    expect(result[0].spend).toBe(1234.56);
    expect(result[0].reportedRevenue).toBe(5000);
  });

  it("returns empty array for empty CSV", () => {
    const csv = `Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value`;
    const result = normalizeMetaAds(csv);
    expect(result).toHaveLength(0);
  });

  it("returns sorted by date", () => {
    const csv = `Day,Campaign name,Amount spent (USD),Purchases,Purchase conversion value
2024-03-01,Campaign A,100,5,500
2024-01-01,Campaign B,100,5,500
2024-02-01,Campaign C,100,5,500`;

    const result = normalizeMetaAds(csv);
    expect(result[0].date).toBe("2024-01-01");
    expect(result[1].date).toBe("2024-02-01");
    expect(result[2].date).toBe("2024-03-01");
  });
});

describe("normalizeGoogleAds", () => {
  it("parses valid Google Ads CSV", () => {
    const csv = `Day,Campaign,Cost,Conversions,Conv. value
2024-01-01,Search - Brand,80.00,4,320.00
2024-01-02,Search - Brand,0,0,0`;

    const result = normalizeGoogleAds(csv);
    expect(result).toHaveLength(2);
    expect(result[0].date).toBe("2024-01-01");
    expect(result[0].spend).toBe(80);
    expect(result[0].reportedConversions).toBe(4);
    expect(result[0].reportedRevenue).toBe(320);
  });

  it("aggregates rows across campaigns", () => {
    const csv = `Day,Campaign,Cost,Conversions,Conv. value
2024-01-01,Campaign A,80,4,320
2024-01-01,Campaign B,20,1,80`;

    const result = normalizeGoogleAds(csv);
    expect(result).toHaveLength(1);
    expect(result[0].spend).toBe(100);
    expect(result[0].reportedConversions).toBe(5);
    expect(result[0].reportedRevenue).toBe(400);
  });
});

describe("normalizeShopifyOrders", () => {
  it("parses valid Shopify CSV and counts each row as one conversion", () => {
    const csv = `Name,Email,Created at,Total
#1001,user@example.com,2024-01-01 10:00:00,50.00
#1002,user2@example.com,2024-01-02,80.00`;

    const result = normalizeShopifyOrders(csv);
    expect(result).toHaveLength(2);
    expect(result[0].date).toBe("2024-01-01");
    expect(result[0].actualConversions).toBe(1);
    expect(result[0].actualRevenue).toBe(50);
    expect(result[1].date).toBe("2024-01-02");
    expect(result[1].actualConversions).toBe(1);
    expect(result[1].actualRevenue).toBe(80);
  });

  it("aggregates multiple orders on the same date", () => {
    const csv = `Name,Email,Created at,Total
#1001,a@b.com,2024-01-01,50.00
#1002,c@d.com,2024-01-01,25.00
#1003,e@f.com,2024-01-02,80.00`;

    const result = normalizeShopifyOrders(csv);
    expect(result).toHaveLength(2);
    expect(result[0].actualConversions).toBe(2);
    expect(result[0].actualRevenue).toBe(75);
  });

  it("handles dates with timestamps", () => {
    const csv = `Name,Email,Created at,Total
#1001,a@b.com,2024-01-01 00:46:08,50.00`;

    const result = normalizeShopifyOrders(csv);
    expect(result[0].date).toBe("2024-01-01");
  });

  it("handles dollar signs in totals", () => {
    const csv = `Name,Email,Created at,Total
#1001,a@b.com,2024-01-01,"$1,234.56"`;

    const result = normalizeShopifyOrders(csv);
    expect(result[0].actualRevenue).toBe(1234.56);
  });
});

describe("normalizeGSC", () => {
  it("parses valid GSC CSV", () => {
    const csv = `Date,Top queries,Clicks,Impressions
2024-01-01,mybrand,10,100
2024-01-01,mybrand shoes,5,50`;

    const result = normalizeGSC(csv);
    expect(result).toHaveLength(1);
    expect(result[0].date).toBe("2024-01-01");
    expect(result[0].brandClicks).toBe(15);
    expect(result[0].brandImpressions).toBe(150);
  });

  it("aggregates across multiple dates", () => {
    const csv = `Date,Top queries,Clicks,Impressions
2024-01-01,mybrand,10,100
2024-01-02,mybrand,5,50`;

    const result = normalizeGSC(csv);
    expect(result).toHaveLength(2);
    expect(result[0].brandClicks).toBe(10);
    expect(result[1].brandClicks).toBe(5);
  });

  it("returns empty array for empty CSV", () => {
    const csv = `Date,Top queries,Clicks,Impressions`;
    const result = normalizeGSC(csv);
    expect(result).toHaveLength(0);
  });
});

describe("mergeAdDaily", () => {
  it("merges Meta and Google Ads data by date", () => {
    const metaAds = [
      { date: "2024-01-01", spend: 100, reportedConversions: 3, reportedRevenue: 300 },
    ];
    const googleAds = [
      { date: "2024-01-01", spend: 50, reportedConversions: 2, reportedRevenue: 200 },
      { date: "2024-01-02", spend: 80, reportedConversions: 2, reportedRevenue: 180 },
    ];

    const result = mergeAdDaily(metaAds, googleAds);
    expect(result).toHaveLength(2);
    expect(result[0].spend).toBe(150);
    expect(result[0].reportedConversions).toBe(5);
    expect(result[0].reportedRevenue).toBe(500);
  });

  it("handles empty metaAds", () => {
    const googleAds = [
      { date: "2024-01-01", spend: 50, reportedConversions: 2, reportedRevenue: 200 },
    ];

    const result = mergeAdDaily([], googleAds);
    expect(result).toHaveLength(1);
    expect(result[0].spend).toBe(50);
  });

  it("handles both empty", () => {
    const result = mergeAdDaily([], []);
    expect(result).toHaveLength(0);
  });
});
