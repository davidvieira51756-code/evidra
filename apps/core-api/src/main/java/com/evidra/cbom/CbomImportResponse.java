package com.evidra.cbom;

import java.util.List;

public record CbomImportResponse(
        String status,
        String bomFormat,
        String specVersion,
        String serialNumber,
        Integer version,
        int componentCount,
        int cryptoAssetCount,
        List<CryptoAsset> cryptoAssets,
        int findingCount,
        List<Finding> findings) {
}
