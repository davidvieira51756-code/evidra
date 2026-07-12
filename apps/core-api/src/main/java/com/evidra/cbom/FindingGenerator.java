package com.evidra.cbom;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import org.springframework.stereotype.Component;

@Component
public class FindingGenerator {

    private static final Set<String> QUANTUM_VULNERABLE_ALGORITHMS = Set.of("RSA", "ECDSA", "ECDH", "DSA", "DH");
    private static final Set<String> POST_QUANTUM_ALGORITHMS = Set.of("ML-KEM", "ML-DSA", "SLH-DSA");
    private static final Map<String, String> ALGORITHM_ALIASES = Map.of(
            "RSA-OAEP", "RSA",
            "RSA-PSS", "RSA");

    public List<Finding> generate(List<CryptoAsset> cryptoAssets) {
        List<Finding> findings = new ArrayList<>();
        for (int index = 0; index < cryptoAssets.size(); index++) {
            CryptoAsset asset = cryptoAssets.get(index);
            findings.add(toFinding(index + 1, asset));
        }
        return List.copyOf(findings);
    }

    private Finding toFinding(int sequence, CryptoAsset asset) {
        String algorithm = asset.algorithm();
        String status = classifyStatus(algorithm);

        return new Finding(
                "finding-" + sequence,
                buildTitle(asset, algorithm),
                cryptoAssetName(asset),
                status,
                buildReason(status, algorithm),
                algorithm,
                asset.componentName(),
                asset.componentVersion(),
                buildRecommendation(status),
                asset.evidence());
    }

    private String buildTitle(CryptoAsset asset, String algorithm) {
        String componentName = asset.componentName() == null ? "unknown component" : asset.componentName();
        if (algorithm == null || algorithm.isBlank()) {
            return "Cryptographic usage detected in " + componentName;
        }
        return algorithm + " usage detected in " + componentName;
    }

    private String cryptoAssetName(CryptoAsset asset) {
        if (asset.componentName() != null && !asset.componentName().isBlank()) {
            return asset.componentName();
        }
        if (asset.algorithm() != null && !asset.algorithm().isBlank()) {
            return asset.algorithm();
        }
        return "unknown crypto asset";
    }

    private String classifyStatus(String algorithm) {
        if (algorithm == null || algorithm.isBlank()) {
            return "REVIEW_REQUIRED";
        }

        String normalizedAlgorithm = normalizeAlgorithm(algorithm);
        if (POST_QUANTUM_ALGORITHMS.contains(normalizedAlgorithm)) {
            return "POST_QUANTUM";
        }

        if (QUANTUM_VULNERABLE_ALGORITHMS.contains(normalizedAlgorithm)) {
            return "QUANTUM_VULNERABLE";
        }

        return "REVIEW_REQUIRED";
    }

    private String normalizeAlgorithm(String algorithm) {
        String normalized = algorithm.trim().toUpperCase(Locale.ROOT);
        return ALGORITHM_ALIASES.getOrDefault(normalized, normalized);
    }

    private String buildReason(String status, String algorithm) {
        return switch (status) {
            case "POST_QUANTUM" -> "The algorithm is explicitly recognized as a post-quantum algorithm.";
            case "QUANTUM_VULNERABLE" -> "The algorithm is explicitly recognized as vulnerable to cryptographically relevant quantum attacks.";
            default -> "The algorithm is not explicitly classified yet, so it requires manual review.";
        };
    }

    private String buildRecommendation(String status) {
        return switch (status) {
            case "POST_QUANTUM" -> "Keep the usage under review and validate interoperability, key management, and performance.";
            case "QUANTUM_VULNERABLE" -> "Assess migration impact and plan a transition path to a post-quantum or hybrid design.";
            default -> "Review the cryptographic usage manually before deciding whether migration is required.";
        };
    }
}
