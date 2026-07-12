package com.evidra.cbom;

import java.util.List;

public record FindingExplanationResponse(
        String findingId,
        String summary,
        String riskExplanation,
        List<String> migrationConsiderations,
        List<String> suggestedTests,
        List<String> limitations) {
}
