package com.evidra.cbom;

import java.io.IOException;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
public class CbomImportService {

    private static final String CYCLONEDX_FORMAT = "CycloneDX";

    private final ObjectMapper objectMapper;

    public CbomImportService(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    public CbomImportResponse importCbom(MultipartFile file) throws IOException {
        if (file == null || file.isEmpty()) {
            throw new CbomImportException("CBOM file is required.");
        }

        JsonNode root = parseJson(file);
        validateCycloneDx(root);

        return new CbomImportResponse(
                "accepted",
                requiredText(root, "bomFormat"),
                requiredText(root, "specVersion"),
                optionalText(root, "serialNumber"),
                optionalInt(root, "version"),
                countArray(root, "components"));
    }

    private JsonNode parseJson(MultipartFile file) throws IOException {
        try {
            return objectMapper.readTree(file.getInputStream());
        } catch (JsonProcessingException exception) {
            throw new CbomImportException("CBOM file must be valid JSON.");
        }
    }

    private void validateCycloneDx(JsonNode root) {
        if (root == null || !root.isObject()) {
            throw new CbomImportException("CBOM file must contain a JSON object.");
        }

        String bomFormat = requiredText(root, "bomFormat");
        if (!CYCLONEDX_FORMAT.equals(bomFormat)) {
            throw new CbomImportException("CBOM file must use CycloneDX bomFormat.");
        }

        requiredText(root, "specVersion");
    }

    private String requiredText(JsonNode root, String fieldName) {
        JsonNode value = root.get(fieldName);
        if (value == null || !value.isTextual() || value.asText().isBlank()) {
            throw new CbomImportException("CBOM file must contain a non-empty " + fieldName + " field.");
        }
        return value.asText();
    }

    private String optionalText(JsonNode root, String fieldName) {
        JsonNode value = root.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        return value.isTextual() ? value.asText() : null;
    }

    private Integer optionalInt(JsonNode root, String fieldName) {
        JsonNode value = root.get(fieldName);
        if (value == null || value.isNull()) {
            return null;
        }
        return value.canConvertToInt() ? value.asInt() : null;
    }

    private int countArray(JsonNode root, String fieldName) {
        JsonNode value = root.get(fieldName);
        if (value == null || !value.isArray()) {
            return 0;
        }
        return value.size();
    }
}
