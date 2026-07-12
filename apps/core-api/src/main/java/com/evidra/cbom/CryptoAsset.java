package com.evidra.cbom;

import java.util.List;

public record CryptoAsset(
        String source,
        String componentName,
        String componentVersion,
        String assetType,
        String algorithm,
        List<String> evidence) {
}
