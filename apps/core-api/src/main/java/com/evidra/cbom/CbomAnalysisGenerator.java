package com.evidra.cbom;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Component;

@Component
public class CbomAnalysisGenerator {

    public CbomAnalysisResponse generate(CbomImportResponse importResponse) {
        CbomAnalysisSummary summary = buildSummary(importResponse);

        return new CbomAnalysisResponse(
                "completed",
                summary,
                importResponse.findings(),
                buildNextActions(summary));
    }

    private CbomAnalysisSummary buildSummary(CbomImportResponse importResponse) {
        return new CbomAnalysisSummary(
                importResponse.bomFormat(),
                importResponse.specVersion(),
                importResponse.componentCount(),
                importResponse.cryptoAssetCount(),
                importResponse.findingCount(),
                countFindingsByStatus(importResponse.findings(), "QUANTUM_VULNERABLE"),
                countFindingsByStatus(importResponse.findings(), "POST_QUANTUM"),
                countFindingsByStatus(importResponse.findings(), "REVIEW_REQUIRED"));
    }

    private int countFindingsByStatus(List<Finding> findings, String status) {
        return (int) findings.stream()
                .filter(finding -> status.equals(finding.status()))
                .count();
    }

    private List<String> buildNextActions(CbomAnalysisSummary summary) {
        List<String> nextActions = new ArrayList<>();

        if (summary.quantumVulnerableFindingCount() > 0) {
            nextActions.add("Review quantum-vulnerable findings and identify affected code paths, data formats, and integrations.");
            nextActions.add("Plan a migration path to post-quantum or hybrid cryptography before changing code.");
        }

        if (summary.reviewRequiredFindingCount() > 0) {
            nextActions.add("Manually review algorithms classified as REVIEW_REQUIRED before assigning migration priority.");
        }

        if (summary.postQuantumFindingCount() > 0) {
            nextActions.add("Validate post-quantum usage for interoperability, key management, payload size, and performance.");
        }

        if (nextActions.isEmpty()) {
            nextActions.add("No cryptographic findings were generated from this CBOM. Validate scanner coverage before treating this as complete.");
        }

        return List.copyOf(nextActions);
    }
}
