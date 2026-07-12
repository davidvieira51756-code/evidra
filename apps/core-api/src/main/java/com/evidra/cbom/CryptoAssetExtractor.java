package com.evidra.cbom;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Component;

@Component
public class CryptoAssetExtractor {

    private static final List<String> CRYPTO_KEYWORDS = List.of(
            "crypto",
            "cryptography",
            "cipher",
            "encrypt",
            "decrypt",
            "signature",
            "certificate",
            "keystore",
            "key",
            "rsa",
            "ecdsa",
            "ecdh",
            "aes",
            "sha",
            "hmac",
            "tls",
            "ml-kem",
            "ml-dsa",
            "slh-dsa");

    public List<CryptoAsset> extract(JsonNode root) {
        JsonNode components = root.get("components");
        if (components == null || !components.isArray()) {
            return List.of();
        }

        List<CryptoAsset> assets = new ArrayList<>();
        for (JsonNode component : components) {
            List<String> evidence = collectEvidence(component);
            if (!evidence.isEmpty()) {
                assets.add(new CryptoAsset(
                        "component",
                        optionalText(component, "name"),
                        optionalText(component, "version"),
                        inferAssetType(component, evidence),
                        inferAlgorithm(component, evidence),
                        evidence));
            }
        }
        return List.copyOf(assets);
    }

    private List<String> collectEvidence(JsonNode component) {
        List<String> evidence = new ArrayList<>();
        addIfCryptoSignal(evidence, "name", optionalText(component, "name"));
        addIfCryptoSignal(evidence, "description", optionalText(component, "description"));
        addIfCryptoSignal(evidence, "purl", optionalText(component, "purl"));

        JsonNode properties = component.get("properties");
        if (properties != null && properties.isArray()) {
            for (JsonNode property : properties) {
                String name = optionalText(property, "name");
                String value = optionalText(property, "value");
                addIfCryptoSignal(evidence, "property:" + name, value);
                addIfCryptoSignal(evidence, "property-name", name);
            }
        }

        return List.copyOf(evidence);
    }

    private void addIfCryptoSignal(List<String> evidence, String fieldName, String value) {
        if (value == null || value.isBlank()) {
            return;
        }

        String normalizedValue = value.toLowerCase(Locale.ROOT);
        boolean hasCryptoSignal = CRYPTO_KEYWORDS.stream().anyMatch(normalizedValue::contains);
        if (hasCryptoSignal) {
            evidence.add(fieldName + "=" + value);
        }
    }

    private String inferAssetType(JsonNode component, List<String> evidence) {
        String componentType = optionalText(component, "type");
        if (componentType != null && !componentType.isBlank()) {
            return componentType;
        }

        return evidence.stream()
                .filter(item -> item.toLowerCase(Locale.ROOT).contains("certificate"))
                .findFirst()
                .map(item -> "certificate")
                .orElse("unknown");
    }

    private String inferAlgorithm(JsonNode component, List<String> evidence) {
        String explicitAlgorithm = findPropertyValue(component, "algorithm");
        if (explicitAlgorithm != null) {
            return explicitAlgorithm;
        }

        return evidence.stream()
                .map(this::findKnownAlgorithm)
                .filter(value -> value != null)
                .findFirst()
                .orElse(null);
    }

    private String findPropertyValue(JsonNode component, String propertyNamePart) {
        JsonNode properties = component.get("properties");
        if (properties == null || !properties.isArray()) {
            return null;
        }

        for (JsonNode property : properties) {
            String name = optionalText(property, "name");
            if (name != null && name.toLowerCase(Locale.ROOT).contains(propertyNamePart)) {
                return optionalText(property, "value");
            }
        }
        return null;
    }

    private String findKnownAlgorithm(String value) {
        String normalizedValue = value.toLowerCase(Locale.ROOT);
        return List.of("ML-KEM", "ML-DSA", "SLH-DSA", "RSA", "ECDSA", "ECDH", "AES", "SHA", "HMAC", "TLS")
                .stream()
                .filter(algorithm -> normalizedValue.contains(algorithm.toLowerCase(Locale.ROOT)))
                .findFirst()
                .orElse(null);
    }

    private String optionalText(JsonNode root, String fieldName) {
        JsonNode value = root.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        return value.isTextual() ? value.asText() : null;
    }
}
