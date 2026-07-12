package com.evidra.cbom;

import java.util.List;

public record Finding(
        String id,
        String title,
        String cryptoAssetName,
        String status,
        String reason,
        String algorithm,
        String componentName,
        String componentVersion,
        String recommendation,
        List<String> evidence) {
}
