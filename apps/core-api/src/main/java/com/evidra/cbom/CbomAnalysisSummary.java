package com.evidra.cbom;

public record CbomAnalysisSummary(
        String bomFormat,
        String specVersion,
        int componentCount,
        int cryptoAssetCount,
        int findingCount,
        int quantumVulnerableFindingCount,
        int postQuantumFindingCount,
        int reviewRequiredFindingCount) {
}
