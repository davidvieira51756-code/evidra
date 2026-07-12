package com.evidra.cbom;

public record CbomImportResponse(
        String status,
        String bomFormat,
        String specVersion,
        String serialNumber,
        Integer version,
        int componentCount) {
}
