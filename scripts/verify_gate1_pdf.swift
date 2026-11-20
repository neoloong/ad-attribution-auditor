// macOS artifact check using the system PDF parser; no external packages.
// swift -module-cache-path /tmp/gate1-swift-cache scripts/verify_gate1_pdf.swift
import Foundation
import PDFKit
import AppKit

let root = URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
let v2 = CommandLine.arguments.contains("--v2")
let evidence = root.appendingPathComponent(v2 ? "validation/v2-artifacts" : "validation/gate1-repair-2026-11-08")
let pdfURL = root.appendingPathComponent("sample/sample-report-2026-11-08.pdf")
let previews = URL(fileURLWithPath: v2 ? "/tmp/ad-auditor-v2-preview-2026-11-09" : "/tmp/ad-auditor-gate1-preview-2026-11-08")
try FileManager.default.createDirectory(at: previews, withIntermediateDirectories: true)
guard let pdf = PDFDocument(url: pdfURL), pdf.pageCount == 4 else {
    fatalError("Expected a readable four-page PDF")
}
let results = try JSONSerialization.jsonObject(with: Data(contentsOf: evidence.appendingPathComponent(v2 ? "sample-data.json" : "results.json"))) as! [String: Any]
var pages: [[String: Any]] = []
var text = ""
for i in 0..<pdf.pageCount {
    let page = pdf.page(at: i)!
    let content = page.string ?? ""
    precondition(content.contains("SAMPLE — synthetic data"), "Missing sample label on page \(i+1)")
    let bounds = page.bounds(for: .mediaBox)
    precondition(bounds.width == 612 && bounds.height == 792)
    pages.append(["page": i + 1, "sample_label_present": true, "extracted_characters": content.count])
    text += content + "\n"
    let thumbnail = page.thumbnail(of: NSSize(width: 918, height: 1188), for: .mediaBox)
    let bitmap = NSBitmapImageRep(cgImage: thumbnail.cgImage(forProposedRect: nil, context: nil, hints: nil)!)
    try bitmap.representation(using: .png, properties: [:])!.write(to: previews.appendingPathComponent("page-\(i+1).png"))
}
let combined = results["combined"] as! [String: Any]
var runs = [combined]
runs += results["campaign_results"] as! [[String: Any]]
var checked: [String] = []
for run in runs {
    let metrics = run["incremental_roas"] as! [String: Any]
    for key in ["reported_roas", "true_incremental_roas"] {
        let token = String(format: "%.4fx", (metrics[key] as! NSNumber).doubleValue)
        precondition(text.contains(token), "Missing engine figure \(token)")
        checked.append(token)
    }
}
for run in runs.dropFirst() {
    precondition(text.contains(run["campaign"] as! String))
}
precondition(text.contains("95% confidence") && text.contains("HC3"))
var intervals: [String] = []
for run in runs {
    let metrics = run["incremental_roas"] as! [String: Any]
    let bounds = metrics["confidence_interval"] as! [NSNumber]
    let token = String(format: "[%.4f, %.4f]x", bounds[0].doubleValue, bounds[1].doubleValue)
    precondition(text.contains(token), "Missing engine CI \(token)")
    intervals.append(token)
}
let reportActions = ["SCALE": "keep", "KILL": "kill", "KEEP": "hold"]
let actionPage = pdf.page(at: 1)!.string ?? ""
for run in runs.dropFirst() {
    let action = results["gate"] as! String == "PASS" ? reportActions[run["action"] as! String]! : "hold"
    precondition(actionPage.contains("\(action) (provisional)"), "Missing provisional action \(action)")
}
precondition(text.contains("SAMPLE — synthetic data"))
if v2 {
    let normalized = text.components(separatedBy: .whitespacesAndNewlines).filter { !$0.isEmpty }.joined(separator: " ")
    precondition(normalized.contains("Assumed contribution margin: 40%"))
    precondition(normalized.contains("Break-even iROAS = 1/margin = 2.50x"))
    precondition(normalized.contains("They are not profit decisions."))
    precondition(normalized.contains("Evidence label: inconclusive"))
    precondition(normalized.contains("Validation v2 supersedes the five-seed Gate-1 PASS"))
    precondition(!normalized.contains("1.0x revenue break-even"))
}
precondition(!text.contains("4.0000x") && !text.contains("0.5000x"), "Truth leaked into customer estimates")
let summary: [String: Any] = [
    "parser": "macOS PDFKit", "page_count": pdf.pageCount, "pages": pages,
    "engine_roas_tokens_verified": checked, "engine_confidence_intervals_verified": intervals,
    "campaign_actions_present": true, "truth_not_substituted_for_engine_estimates": true,
    "v2_margin_and_classification_verified": v2,
    "preview_directory": previews.path,
]
let out = try JSONSerialization.data(withJSONObject: summary, options: [.prettyPrinted, .sortedKeys])
try out.write(to: evidence.appendingPathComponent("pdf-verification.json"))
try text.write(to: previews.appendingPathComponent("extracted-text.txt"), atomically: true, encoding: .utf8)
print(String(data: out, encoding: .utf8)!)
