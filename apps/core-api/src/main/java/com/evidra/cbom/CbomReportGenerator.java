package com.evidra.cbom;

import org.springframework.stereotype.Component;

@Component
public class CbomReportGenerator {

    public String generate(CbomImportResponse importResponse) {
        StringBuilder report = new StringBuilder();
        report.append("# Evidra CBOM Report\n\n");
        report.append("## Summary\n\n");
        appendLine(report, "- Status: " + importResponse.status());
        appendLine(report, "- Format: " + importResponse.bomFormat());
        appendLine(report, "- Spec version: " + importResponse.specVersion());
        appendLine(report, "- Components: " + importResponse.componentCount());
        appendLine(report, "- Crypto assets: " + importResponse.cryptoAssetCount());
        appendLine(report, "- Findings: " + importResponse.findingCount());

        report.append("\n## Findings\n\n");
        if (importResponse.findings().isEmpty()) {
            report.append("No cryptographic findings were generated.\n");
            return report.toString();
        }

        for (Finding finding : importResponse.findings()) {
            report.append("### ").append(finding.title()).append("\n\n");
            appendLine(report, "- ID: " + finding.id());
            appendLine(report, "- Crypto asset: " + finding.cryptoAssetName());
            appendLine(report, "- Status: " + finding.status());
            appendLine(report, "- Algorithm: " + valueOrUnknown(finding.algorithm()));
            appendLine(report, "- Component: " + valueOrUnknown(finding.componentName()));
            appendLine(report, "- Component version: " + valueOrUnknown(finding.componentVersion()));
            appendLine(report, "- Reason: " + finding.reason());
            appendLine(report, "- Recommendation: " + finding.recommendation());
            report.append("\n");
        }

        return report.toString();
    }

    private void appendLine(StringBuilder report, String line) {
        report.append(line).append("\n");
    }

    private String valueOrUnknown(String value) {
        if (value == null || value.isBlank()) {
            return "unknown";
        }
        return value;
    }
}
