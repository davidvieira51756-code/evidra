package com.evidra.cbom;

import java.util.List;

public record CbomAnalysisResponse(
        String status,
        CbomAnalysisSummary summary,
        List<Finding> findings,
        List<String> nextActions) {
}
